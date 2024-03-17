from __future__ import annotations

import contextlib
from datetime import datetime  # noqa: TCH003
from typing import Annotated, Any, Final

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)

from radiofeed.feedparser.date_parser import parse_date

_PG_INTEGER_RANGE: Final = range(
    -2147483648,
    2147483647,
)

_AUDIO_MIMETYPES: Final = frozenset(
    [
        "audio/aac",
        "audio/aacp",
        "audio/basic",
        "audio/L24",
        "audio/m4a",
        "audio/midi",
        "audio/mp3",
        "audio/mp4",
        "audio/mp4a-latm",
        "audio/mp4a-latm",
        "audio/mpef",
        "audio/mpeg",
        "audio/mpeg3",
        "audio/mpeg4",
        "audio/mpg",
        "audio/ogg",
        "audio/video",
        "audio/vnd.dlna.adts",
        "audio/vnd.rn-realaudio",
        "audio/vnd.wave",
        "audio/vorbis",
        "audio/wav",
        "audio/wave",
        "audio/webm",
        "audio/x-aac",
        "audio/x-aiff",
        "audio/x-aiff",
        "audio/x-flac",
        "audio/x-hx-aac-adts",
        "audio/x-m4a",
        "audio/x-m4a",
        "audio/x-m4b",
        "audio/x-m4v",
        "audio/x-mov",
        "audio/x-mp3",
        "audio/x-mpeg",
        "audio/x-mpg",
        "audio/x-ms-wma",
        "audio/x-pn-realaudio",
        "audio/x-wav",
    ]
)


_url_validator = URLValidator(["http", "https"])


def pg_integer(value: Any) -> int | None:
    """Check is an integer, and ensure within Postgres integer range values."""
    try:
        value = int(value) if value else None
        assert value in _PG_INTEGER_RANGE
        return value
    except ValueError:
        return None


def language(value: str) -> str:
    """Returns two-character language code."""
    return value[:2].casefold()


def explicit(value: str | None) -> bool:
    """Checks if podcast or episode explicit."""
    return bool(value and value.casefold() in ("clean", "yes"))


def url(value: str | None) -> str | None:
    """Returns a URL value. Will try to prefix with https:// if only domain provided.

    If cannot resolve as a valid URL will return None.

    Args:
        value (str | None)

    Returns:
        str | None
    """
    if value:
        if not value.startswith("http"):
            value = f"http://{value}"

        with contextlib.suppress(ValidationError):
            _url_validator(value)
            return value
    return None


def duration(value: str | None) -> str:
    """Given a duration value will ensure all values fall within range.

    Examples:
        - 3600 (plain int) -> "3600"
        - 3:60:50:1000 -> "3:60:50"

    Return empty string if cannot resolve.

    Args:
        value (str | None)

    Returns:
        str
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
            [str(v) for v in [int(v) for v in value.split(":")[:3]] if v in range(60)]
        )

    except ValueError:
        return ""


Explicit = Annotated[bool, BeforeValidator(explicit)]
Language = Annotated[str, BeforeValidator(language)]
PgInteger = Annotated[int | None, BeforeValidator(pg_integer)]
Duration = Annotated[str | None, BeforeValidator(duration)]
Url = Annotated[str, BeforeValidator(url)]
Complete = Annotated[bool, TypeAdapter(bool).validate_python("yes")]


class Item(BaseModel):
    """Individual item or episode in RSS or Atom podcast feed."""

    guid: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)

    categories: list[str] = Field(default_factory=list)

    description: str = ""
    keywords: str = ""

    pub_date: datetime

    media_url: Url
    media_type: str

    website: Url | None = None

    explicit: Explicit = False

    length: PgInteger | None = None
    duration: Duration = None

    season: PgInteger | None = None
    episode: PgInteger | None = None

    episode_type: str = "full"

    cover_url: Url | None = None

    @field_validator("pub_date", mode="before")
    @classmethod
    def validate_pub_date(cls, value: Any) -> datetime:
        """Validates pub date."""
        value = parse_date(value)
        if value is None:
            raise ValueError("pub_date cannot be none")
        if value > timezone.now():
            raise ValueError("pub_date cannot be in the future")
        return value

    @field_validator("media_type", mode="before")
    @classmethod
    def validate_media_type(cls, value: Any) -> str:
        """Validates media type."""
        assert value in _AUDIO_MIMETYPES
        return value

    @model_validator(mode="after")
    def validate_keywords(self) -> Item:
        """Set default keywords."""
        self.keywords = " ".join(filter(None, self.categories))
        return self


class Feed(BaseModel):
    """RSS/Atom Feed model."""

    title: str = Field(..., min_length=1)
    owner: str = ""
    description: str = ""

    items: list[Item]
    pub_date: datetime | None = None

    language: Language = "en"
    website: Url | None = None
    cover_url: Url | None = None

    funding_text: str = ""
    funding_url: str | None = None

    explicit: Explicit = False
    complete: Complete = False

    categories: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_pub_date(self) -> Feed:
        """Set default pub date based on number of items."""
        self.pub_date = max(item.pub_date for item in self.items)
        return self
