from datetime import datetime
from typing import Any, ClassVar

from django.utils import timezone
from django.utils.text import slugify
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)

from simplecasts.episodes.models import Episode
from simplecasts.podcasts import tokenizer
from simplecasts.podcasts.models import Podcast
from simplecasts.podcasts.parsers.date_parser import parse_date
from simplecasts.podcasts.parsers.fields import (
    AudioMimetype,
    EmptyIfNone,
    EpisodeType,
    Explicit,
    OptionalUrl,
    PgInteger,
    PodcastType,
)
from simplecasts.podcasts.parsers.validators import is_one_of, normalize_url


class Item(BaseModel):
    """Individual item or episode in RSS or Atom podcast feed."""

    guid: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)

    description: EmptyIfNone = ""
    keywords: EmptyIfNone = ""

    pub_date: datetime

    media_url: str
    media_type: AudioMimetype

    cover_url: OptionalUrl = ""
    website: OptionalUrl = ""

    explicit: Explicit = False

    file_size: PgInteger = None

    duration: str = ""

    season: PgInteger = None
    episode: PgInteger = None

    episode_type: EpisodeType = Episode.EpisodeType.FULL

    @field_validator("pub_date", mode="before")
    @classmethod
    def validate_pub_date(cls, value: Any) -> datetime:
        """Checks is valid datetime value and not in the future."""
        value = parse_date(value)
        if value is None:
            raise ValueError("pub_date cannot be none")
        if value > timezone.now():
            raise ValueError("pub_date cannot be in future")
        return value

    @field_validator("media_url", mode="after")
    @classmethod
    def validate_media_url(cls, value: Any) -> str:
        """Validate media url"""
        if value := normalize_url(value):
            return value
        raise ValueError("url is required")

    @field_validator("duration", mode="before")
    @classmethod
    def validate_duration(cls, value: Any) -> str:
        """Given a duration value will ensure all values fall within range.

        Examples:
            - 3600 (plain int) -> "3600"
            - 3:60:50:1000 -> "3:60:50"

        Return empty string if cannot resolve.
        """
        if not value:
            return ""

        try:
            # plain seconds value
            return str(int(value))
        except ValueError:
            pass

        try:
            return ":".join(
                [
                    str(v)
                    for v in [int(v) for v in value.split(":")[:3]]
                    if v in range(60)
                ]
            )

        except ValueError:
            return ""


class Feed(BaseModel):
    """RSS/Atom Feed model."""

    DEFAULT_LANGUAGE: ClassVar[str] = "en"

    title: str = Field(..., min_length=1)

    owner: EmptyIfNone = ""
    description: EmptyIfNone = ""

    language: str = DEFAULT_LANGUAGE
    pub_date: datetime | None = None

    canonical_url: OptionalUrl = ""
    website: OptionalUrl = ""
    cover_url: OptionalUrl = ""

    funding_text: EmptyIfNone = ""
    funding_url: OptionalUrl = ""

    keywords: EmptyIfNone = ""

    explicit: Explicit = False
    complete: bool = False

    podcast_type: PodcastType = Podcast.PodcastType.EPISODIC

    categories: set[str] = Field(default_factory=set)

    items: list[Item]

    @field_validator("language", mode="before")
    @classmethod
    def validate_language(cls, value: Any) -> str:
        """Validate media type."""
        if value and len(value) > 1:
            value = value.casefold()[:2]
            if value in tokenizer.get_language_codes():
                return value
        return cls.DEFAULT_LANGUAGE

    @field_validator("complete", mode="before")
    @classmethod
    def validate_complete(cls, value: Any) -> bool:
        """Validate complete."""
        return is_one_of(value, values=("yes", "true"))

    @field_validator("categories", mode="before")
    @classmethod
    def validate_categories(cls, value: Any) -> set[str]:
        """Ensure categories are sorted.

        1. Normalize categories by stripping whitespace and casefolding.
        2. Replace "&amp;/and" and with " & "
        3. Split categories on common separators and add to set.
        4. Slugify categories to ensure consistent format.
        """
        categories = set()
        for category in value:
            if (
                normalized := category.strip()
                .casefold()
                .replace(" &amp; ", " & ")
                .replace(" and ", " & ")
            ):
                categories.add(normalized)
                for sep in (" ", "/", "&", ",", "+"):
                    categories.update(normalized.split(sep))
        # Slugify keywords to ensure consistent format
        return {c for c in (slugify(c, allow_unicode=False) for c in categories) if c}

    @model_validator(mode="after")
    def validate_pub_date(self) -> "Feed":
        """Set default pub date based on max items pub date."""
        self.pub_date = max(self.pub_dates)
        return self

    @property
    def pub_dates(self) -> list[datetime]:
        """Return sorted list of pub dates for all items in feed."""
        return [item.pub_date for item in self.items]

    def tokenize(self) -> str:
        """Tokenize feed for search."""
        text = " ".join(
            [
                value
                for value in [
                    self.title,
                    self.description,
                    self.owner,
                    *self.categories,
                    *self.keywords.split(","),
                    *[item.title for item in self.items][:6],
                ]
                if value
            ]
        )
        return " ".join(tokenizer.tokenize(self.language, text))
