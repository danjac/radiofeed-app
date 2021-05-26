from __future__ import annotations

import dataclasses

from datetime import datetime
from functools import lru_cache
from typing import Any

import requests

from django.core.exceptions import ValidationError
from django.core.files.images import ImageFile
from django.core.validators import MaxLengthValidator, RegexValidator, URLValidator
from django.utils import timezone

from audiotrails.episodes.models import Episode
from audiotrails.podcasts.models import Category, Podcast
from audiotrails.podcasts.recommender.text_parser import extract_keywords
from audiotrails.podcasts.rss_parser import http
from audiotrails.podcasts.rss_parser.date_parser import parse_date
from audiotrails.podcasts.rss_parser.exceptions import InvalidImageURL
from audiotrails.podcasts.rss_parser.image import fetch_image_from_url

CategoryDict = dict[str, Category]


@lru_cache
def get_categories_dict() -> CategoryDict:
    return {c.name: c for c in Category.objects.all()}


@dataclasses.dataclass
class Audio:

    type: str
    url: str
    length: int | None = None
    rel: str = ""

    def __post_init__(self) -> None:
        _validate_url(self.url)
        _validate_audio_type(self.type)
        _validate_audio_type_length(self.type)


@dataclasses.dataclass
class Item:
    audio: Audio | None

    title: str
    guid: str
    duration: str

    raw_pub_date: str

    explicit: bool = False
    description: str = ""

    link: str = ""
    keywords: str = ""

    pub_date: datetime | None = None

    def __post_init__(self) -> None:
        if (pub_date := parse_date(self.raw_pub_date)) is None:
            raise ValidationError("missing or invalid date")

        if self.audio is None:
            raise ValidationError("missing audio")

        _validate_duration_length(self.duration)

        self.pub_date = pub_date
        self.link = _clean_url(self.link)

    def make_episode(self, **kwargs) -> Episode:
        return Episode(
            pub_date=self.pub_date,
            guid=self.guid,
            title=self.title,
            duration=self.duration,
            explicit=self.explicit,
            description=self.description,
            keywords=self.keywords,
            link=self.link,
            media_url=self.audio.url,
            media_type=self.audio.type,
            length=self.audio.length or None,
            **kwargs,
        )


@dataclasses.dataclass
class Feed:
    title: str
    description: str
    creators: set[str]
    image: str | None
    categories: list[str]
    items: list[Item]

    explicit: bool = False

    language: str = "en"
    link: str = ""

    def __post_init__(self) -> None:
        if len(self.items) == 0:
            raise ValidationError("Must be at least one item")

        self.link = _clean_url(self.link)

        self.language = (
            self.language.replace("-", "").strip()[:2] if self.language else "en"
        ).lower()

    def sync_podcast(
        self,
        podcast: Podcast,
        force_update: bool,
        extra_kwargs: dict[str, Any] | None = None,
    ) -> list[Episode]:
        """Sync podcast data with feed. Returns list of new episodes."""

        pub_date = self.get_pub_date()

        if not self.should_update(podcast, pub_date, force_update):
            return []

        # timestamps
        podcast.pub_date = pub_date
        podcast.last_updated = timezone.now()

        # description
        podcast.title = self.title
        podcast.description = self.description
        podcast.link = self.link
        podcast.language = self.language
        podcast.explicit = self.explicit
        podcast.creators = self.get_creators()

        # keywords
        categories_dct = get_categories_dict()
        categories = self.get_categories(categories_dct)

        podcast.keywords = self.get_keywords(categories_dct)
        podcast.extracted_text = self.extract_text(podcast, categories)

        # reset errors
        podcast.sync_error = ""
        podcast.num_retries = 0

        # image
        if image := self.fetch_cover_image(podcast, force_update):
            podcast.cover_image = image
            podcast.cover_image_date = timezone.now()

        # any other attrs
        for k, v in (extra_kwargs or {}).items():
            setattr(podcast, k, v)

        podcast.save()

        podcast.categories.set(categories)  # type: ignore

        # episodes
        return self.create_episodes(podcast)

    def should_update(
        self,
        podcast: Podcast,
        pub_date: datetime | None,
        force_update: bool,
    ) -> bool:

        if pub_date is None:
            return False

        return any(
            (
                force_update,
                podcast.last_updated is None,
                podcast.last_updated and podcast.last_updated < pub_date,
            )
        )

    def create_episodes(self, podcast: Podcast) -> list[Episode]:
        """Parses new episodes from podcast feed. Remove any episodes
        no longer in the feed."""

        episodes = Episode.objects.filter(podcast=podcast)

        # remove any episodes that may have been deleted on the podcast
        episodes.exclude(guid__in=[item.guid for item in self.items]).delete()

        guids = episodes.values_list("guid", flat=True)

        return Episode.objects.bulk_create(
            [
                item.make_episode(podcast=podcast)
                for item in self.items
                if item.guid not in guids
            ],
            ignore_conflicts=True,
        )

    def get_creators(self) -> str:
        return ", ".join(
            {
                c
                for c in {
                    c.lower(): c for c in [c.strip() for c in self.creators]
                }.values()
                if c
            }
        )

    def get_categories(self, categories_dct: CategoryDict) -> list[Category]:
        return [
            categories_dct[name] for name in self.categories if name in categories_dct
        ]

    def get_keywords(self, categories_dct: CategoryDict) -> str:
        return " ".join(name for name in self.categories if name not in categories_dct)

    def extract_text(self, podcast: Podcast, categories: list[Category]) -> str:
        """Extract keywords from text content for recommender"""
        text = " ".join(
            [
                podcast.title,
                podcast.description,
                podcast.keywords,
                podcast.creators,
            ]
            + [c.name for c in categories]
            + [item.title for item in self.items][:6]
        )
        return " ".join(extract_keywords(podcast.language, text))

    def get_pub_date(self) -> datetime | None:
        now = timezone.now()
        try:
            return max(item.pub_date for item in self.items if item.pub_date < now)
        except ValueError:
            return None

    def fetch_cover_image(
        self, podcast: Podcast, force_update: bool
    ) -> ImageFile | None:
        if not self.should_update_image(podcast, force_update):
            return None

        try:
            return fetch_image_from_url(self.image)
        except InvalidImageURL:
            pass

        return None

    def should_update_image(self, podcast: Podcast, force_update: bool) -> bool:
        if not self.image:
            return False

        if force_update:
            return True

        if not podcast.cover_image or not podcast.cover_image_date:
            return True

        try:
            headers = http.get_headers(self.image)
        except requests.RequestException:
            return False

        if (
            last_modified := parse_date(headers.get("Last-Modified", None))
        ) and last_modified > podcast.cover_image_date:
            return True

        # a lot of CDNs just return Date as current date/time so not very useful.
        # in this case only update if older than 30 days.

        if (date := parse_date(headers.get("Date", None))) and (
            date - podcast.cover_image_date
        ).days > 30:
            return True

        return False


def _clean_url(url: str | None) -> str:

    if not url:
        return ""

    # links often just consist of domain: try prefixing http://
    if not url.startswith("http"):
        url = "http://" + url

    # if not a valid URL, just make empty string
    try:
        _validate_url(url)
        _validate_url_length(url)
    except ValidationError:
        return ""

    return url


# validators

_validate_audio_type_length = MaxLengthValidator(60)
_validate_audio_type = RegexValidator(r"^audio/*")
_validate_duration_length = MaxLengthValidator(30)
_validate_url_length = MaxLengthValidator(500)
_validate_url = URLValidator(schemes=["http", "https"])
