from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from django.core.validators import URLValidator
from django.utils import timezone
from pydantic import BaseModel, Field, TypeAdapter, field_validator, model_validator

from radiofeed.feedparser import converters, validators
from radiofeed.feedparser.date_parser import parse_date

_url_validator = URLValidator(["http", "https"])

Explicit = Annotated[bool, converters.explicit]
Complete = Annotated[bool, TypeAdapter(bool).validate_python("yes")]

if TYPE_CHECKING:  # pragma: no cover
    from datetime import datetime


def validate_url(value: Any) -> str:
    """Checks if value is a valid URL.

    Raises:
        ValueError: invalid URL
    """
    if value:
        _url_validator(value)
    return value


class Item(BaseModel):
    """Individual item or episode in RSS or Atom podcast feed."""

    guid: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)

    categories: list[str] = Field(default_factory=list)

    description: str = ""
    keywords: str = ""

    pub_date: datetime

    media_url: str
    media_type: str

    website: str | None = None

    explicit: Explicit = False

    length: int | None = None
    duration: str | None = None

    season: int | None = None
    episode: int | None = None
    episode_type: str = "full"

    cover_url: str | None = None

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

    @field_validator("length", mode="before")
    @classmethod
    def validate_length(cls, value: Any) -> int | None:
        """Validates length."""
        try:
            return int(value) if value else None
        except ValueError:
            return None

    @field_validator("media_type", mode="before")
    @classmethod
    def validate_media_type(cls, value: Any) -> str:
        """Validates media type."""
        assert value in validators._AUDIO_MIMETYPES
        return value

    @field_validator("media_url", mode="before")
    @classmethod
    def validate_media_url(cls, value: Any) -> str:
        """Validates media url."""
        if not (value := converters.url(value)):
            raise ValueError("media_url required")
        return validate_url(value)

    @field_validator("cover_url", mode="before")
    @classmethod
    def validate_cover_url(cls, value: Any) -> str:
        """Validates media url."""
        return validate_url(converters.url(value))

    @field_validator("website", mode="before")
    @classmethod
    def validate_website(cls, value: Any) -> str | None:
        """Validate website."""
        if website := converters.url(value):
            return website
        return None

    @field_validator("duration", mode="before")
    @classmethod
    def validate_duration(cls, value: Any) -> str:
        """Validate duration"""
        return converters.duration(value)

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

    language: str = "en"
    website: str | None = None
    cover_url: str | None = None

    funding_text: str = ""
    funding_url: str | None = None

    explicit: Explicit = False
    complete: Complete = False

    categories: list[str] = Field(default_factory=list)

    @field_validator("cover_url", mode="before")
    @classmethod
    def validate_cover_url(cls, value: Any) -> str:
        """Validates media url."""
        return validate_url(converters.url(value))

    @field_validator("language", mode="before")
    @classmethod
    def validate_language(cls, value: Any) -> str:
        """Validates media url."""
        return converters.language(value) if value else "en"

    @field_validator("website", mode="before")
    @classmethod
    def validate_website(cls, value: Any) -> str | None:
        """Validate website."""
        if website := converters.url(value):
            return website
        return None

    @model_validator(mode="after")
    def validate_pub_date(self) -> Feed:
        """Set default pub date based on number of items."""
        self.pub_date = max(item.pub_date for item in self.items)
        return self
