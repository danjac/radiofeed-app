import contextlib
import functools
from collections.abc import Iterable
from datetime import datetime
from typing import Annotated, Any, ClassVar, Final, TypeVar

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db.models import TextChoices
from django.utils import timezone
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    Field,
    field_validator,
    model_validator,
)

from radiofeed import tokenizer
from radiofeed.episodes.audio_types import AudioMimetype
from radiofeed.episodes.models import Episode
from radiofeed.feedparser.date_parser import parse_date
from radiofeed.podcasts.models import Podcast

T = TypeVar("T")


_PG_INTEGER_RANGE: Final = range(
    -2147483648,
    2147483647,
)


_url_validator = URLValidator(["http", "https"])


def _pg_integer(value: Any) -> int | None:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None

    if value not in _PG_INTEGER_RANGE:
        return None
    return value


def _one_of(value: str | None, *, values: Iterable[str]) -> bool:
    return bool(value and value.casefold() in values)


def _default_if_none(value: Any, *, default: T) -> T:
    return default if value is None else value


def _one_of_choices(
    value: str | None,
    *,
    choices: type[TextChoices],
    default: str,
) -> str:
    if (value := (value or "").casefold()) in choices:
        return value
    return default


def _url(value: str | None) -> str:
    if value:
        if not value.startswith("http"):
            value = f"http://{value}"

        with contextlib.suppress(ValidationError):
            _url_validator(value)
            return value
    return ""


OptionalUrl = Annotated[str | None, AfterValidator(_url)]

PgInteger = Annotated[int | None, BeforeValidator(_pg_integer)]

Explicit = Annotated[
    bool,
    BeforeValidator(
        functools.partial(_one_of, values=("clean", "yes", "true")),
    ),
]

EmptyIfNone = Annotated[
    str, BeforeValidator(functools.partial(_default_if_none, default=""))
]

EpisodeType = Annotated[
    str,
    BeforeValidator(
        functools.partial(
            _one_of_choices,
            choices=Episode.EpisodeType,
            default=Episode.EpisodeType.FULL,
        )
    ),
]

PodcastType = Annotated[
    str,
    BeforeValidator(
        functools.partial(
            _one_of_choices,
            choices=Podcast.PodcastType,
            default=Podcast.PodcastType.EPISODIC,
        )
    ),
]


class Item(BaseModel):
    """Individual item or episode in RSS or Atom podcast feed."""

    guid: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)

    categories: set[str] = Field(default_factory=set)

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

    @field_validator("categories", mode="after")
    @classmethod
    def validate_categories(cls, value: Any) -> set[str]:
        """Ensure categories are unique and not empty."""
        return {c.casefold() for c in set(filter(None, value))}

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
        if not _url(value):
            raise ValueError("url is required")
        return value

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

    @model_validator(mode="after")
    def validate_keywords(self) -> "Item":
        """Set default keywords."""
        self.keywords = " ".join(filter(None, self.categories))
        return self


class Feed(BaseModel):
    """RSS/Atom Feed model."""

    DEFAULT_LANGUAGE: ClassVar = "en"

    title: str = Field(..., min_length=1)

    owner: EmptyIfNone = ""
    description: EmptyIfNone = ""

    language: str = DEFAULT_LANGUAGE
    pub_date: datetime | None = None

    website: OptionalUrl = ""
    cover_url: OptionalUrl = ""

    funding_text: EmptyIfNone = ""
    funding_url: OptionalUrl = ""

    explicit: Explicit = False
    complete: bool = False

    items: list[Item]

    categories: set[str] = Field(default_factory=set)

    podcast_type: PodcastType = Podcast.PodcastType.EPISODIC

    @field_validator("language", mode="before")
    @classmethod
    def validate_language(cls, value: Any) -> str:
        """Validate media type."""
        return (
            value.casefold()[:2] if value and len(value) > 1 else cls.DEFAULT_LANGUAGE
        )

    @field_validator("categories", mode="after")
    @classmethod
    def validate_categories(cls, value: Any) -> set[str]:
        """Ensure categories are unique and not empty."""
        return {c.casefold() for c in set(filter(None, value))}

    @field_validator("complete", mode="before")
    @classmethod
    def validate_complete(cls, value: Any) -> bool:
        """Validate complete."""
        return _one_of(value, values=("yes", "true"))

    @model_validator(mode="after")
    def validate_pub_date(self) -> "Feed":
        """Set default pub date based on max items pub date."""
        self.pub_date = max([item.pub_date for item in self.items])
        return self

    def tokenize(self) -> str:
        """Tokenize feed for search."""
        text = " ".join(
            value
            for value in [
                self.title,
                self.description,
                self.owner,
            ]
            + list(self.categories)
            + [item.title for item in self.items][:6]
            if value
        )
        return " ".join(tokenizer.tokenize(self.language, text))
