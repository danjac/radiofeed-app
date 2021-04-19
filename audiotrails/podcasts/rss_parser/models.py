import datetime

from functools import lru_cache
from typing import List, Optional, Set

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone
from pydantic import BaseModel, HttpUrl, conlist, constr, validator

from audiotrails.episodes.models import Episode

from ..models import Category
from ..recommender.text_parser import extract_keywords
from .date_parser import parse_date
from .exceptions import InvalidImageURL
from .image import fetch_image_from_url


@lru_cache
def get_categories_dict():
    return {c.name: c for c in Category.objects.all()}


class Audio(BaseModel):
    type: constr(max_length=60)  # type: ignore
    url: HttpUrl
    length: Optional[int]

    @validator("type")
    def is_audio(cls, value):
        if not value.startswith("audio/"):
            raise ValueError("not a valid audio media")

        return value


class Item(BaseModel):
    audio: Audio
    title: str
    guid: str
    explicit: bool = False
    description: str = ""
    keywords: str = ""
    link: constr(max_length=500) = ""  # type: ignore
    pub_date: datetime.datetime
    duration: constr(max_length=30)  # type: ignore

    @validator("pub_date", pre=True)
    def parse_date(cls, value):
        if (pub_date := parse_date(value)) is None:
            raise ValueError("missing or invalid date")
        return pub_date

    def make_episode(self, **kwargs):
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
            length=self.audio.length,
            **kwargs,
        )


class Feed(BaseModel):
    title: str
    description: str
    explicit: bool = False
    language: str = "en"
    link: constr(max_length=500) = ""  # type: ignore
    items: conlist(Item, min_items=1)  # type: ignore
    creators: Set[str]
    image: Optional[str]
    categories: List[str]

    @validator("language")
    def language_code(cls, value):
        return (value.replace("-", "").strip()[:2] if value else "en").lower()

    @validator("link", pre=True)
    def prepare_link(cls, value: str):
        if not value:
            return value

        # links often just consist of domain: try prefixing http://
        if not value.startswith("http"):
            value = "http://" + value

        # if not a valid URL, just return empty string
        try:
            URLValidator(value)
        except ValidationError:
            return ""

        return value

    def sync_podcast(self, podcast, etag, force_update):
        """Sync podcast data with feed. Returns list of new episodes."""

        pub_date = self.get_pub_date()

        if not self.do_update(podcast, pub_date, force_update):
            return []

        # timestamps
        podcast.etag = etag
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
        if not podcast.cover_image:
            podcast.cover_image = self.fetch_cover_image()

        podcast.save()
        podcast.categories.set(categories)

        # episodes
        return self.create_episodes(podcast)

    def do_update(
        self,
        podcast,
        pub_date,
        force_update,
    ):

        if pub_date is None:
            return False

        return any(
            (
                force_update,
                podcast.last_updated is None,
                podcast.last_updated and podcast.last_updated < pub_date,
            )
        )

    def create_episodes(self, podcast):
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

    def get_creators(self):
        return ", ".join(
            {c.lower(): c for c in [c.strip() for c in self.creators]}.values()
        )

    def get_categories(self, categories_dct):
        return [
            categories_dct[name] for name in self.categories if name in categories_dct
        ]

    def get_keywords(self, categories_dct):
        return " ".join(name for name in self.categories if name not in categories_dct)

    def extract_text(self, podcast, categories):
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

    def get_pub_date(self):
        now = timezone.now()
        try:
            return max(item.pub_date for item in self.items if item.pub_date < now)
        except ValueError:
            return None

    def fetch_cover_image(self):
        if not self.image:
            return None

        try:
            return fetch_image_from_url(self.image)
        except InvalidImageURL:
            pass

        return None
