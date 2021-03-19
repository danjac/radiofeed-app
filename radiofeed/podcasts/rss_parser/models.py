import datetime

from functools import lru_cache
from typing import Dict, List, Optional, Set

from django.core.exceptions import ValidationError
from django.core.files.images import ImageFile
from django.core.validators import URLValidator
from django.utils import timezone
from pydantic import BaseModel, HttpUrl, conlist, constr, validator

from radiofeed.episodes.models import Episode

from ..models import Category, Podcast
from ..recommender.text_parser import extract_keywords
from .date_parser import parse_date
from .exceptions import InvalidImageURL
from .image import fetch_image_from_url

CategoryDict = Dict[str, Category]


@lru_cache
def get_categories_dict() -> CategoryDict:
    return {c.name: c for c in Category.objects.all()}


class Audio(BaseModel):
    type: constr(max_length=60)  # type: ignore
    url: HttpUrl
    length: Optional[int]

    @validator("type")
    def is_audio(cls, value: str) -> str:
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
    def parse_date(cls, value: Optional[str]) -> datetime.datetime:
        if (pub_date := parse_date(value)) is None:
            raise ValueError("missing or invalid date")
        return pub_date

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
    authors: Set[str]
    image: Optional[str]
    categories: List[str]

    @validator("language")
    def language_code(cls, value: str) -> str:
        return (value[:2] if value else "en").strip().lower()

    @validator("link", pre=True)
    def prepare_link(cls, value: str) -> str:
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

    def update_podcast(
        self, podcast: Podcast, etag: str, force_update: bool
    ) -> List[Episode]:
        """Sync podcast data with feed. Returns list of new episodes."""

        pub_date = self.get_pub_date()

        if not self.do_update(podcast, pub_date, force_update):
            return []

        new_episodes = self.create_episodes(podcast)

        if new_episodes:
            pub_date = max(e.pub_date for e in new_episodes)

        categories_dct = get_categories_dict()

        categories = self.get_categories(categories_dct)
        podcast.categories.set(categories)

        kwargs = {
            "etag": etag,
            "pub_date": pub_date,
            "last_updated": timezone.now(),
            "title": self.title,
            "description": self.description,
            "link": self.link,
            "language": self.language,
            "explicit": self.explicit,
            "authors": ", ".join(self.authors),
            "keywords": self.get_keywords(categories_dct),
            "extracted_text": self.extract_text(podcast, categories),
            "sync_error": "",
            "num_retries": 0,
        }

        if not podcast.cover_image:
            kwargs["cover_image"] = self.fetch_cover_image()

        Podcast.objects.filter(pk=podcast.id).update(**kwargs)

        return new_episodes

    def do_update(
        self,
        podcast: Podcast,
        pub_date: Optional[datetime.datetime],
        force_update: bool,
    ) -> bool:

        if pub_date is None:
            return False

        if (
            not force_update
            and podcast.last_updated
            and podcast.last_updated > pub_date
        ):
            return False

        return True

    def create_episodes(self, podcast: Podcast) -> List[Episode]:
        """Parses new episodes from podcast feed."""
        guids = podcast.episode_set.values_list("guid", flat=True)

        return Episode.objects.bulk_create(
            [
                item.make_episode(podcast=podcast)
                for item in self.items
                if item.guid not in guids
            ],
            ignore_conflicts=True,
        )

    def get_categories(self, categories_dct: CategoryDict) -> List[Category]:
        return [
            categories_dct[name] for name in self.categories if name in categories_dct
        ]

    def get_keywords(self, categories_dct: CategoryDict) -> str:
        return " ".join(
            [name for name in self.categories if name not in categories_dct]
        )

    def extract_text(self, podcast: Podcast, categories: List[Category]) -> str:
        """Extract keywords from text content for recommender"""
        text = " ".join(
            [
                podcast.title,
                podcast.description,
                podcast.keywords,
                podcast.authors,
            ]
            + [c.name for c in categories]
            + [item.title for item in self.items][:6]
        )
        return " ".join([kw for kw in extract_keywords(podcast.language, text)])

    def get_pub_date(self) -> Optional[datetime.datetime]:
        now = timezone.now()
        try:
            return max([item.pub_date for item in self.items if item.pub_date < now])
        except ValueError:
            return None

    def fetch_cover_image(self) -> Optional[ImageFile]:
        if not self.image:
            return None

        try:
            return fetch_image_from_url(self.image)
        except InvalidImageURL:
            pass

        return None
