from __future__ import annotations

import functools
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field, field_validator, model_validator

from radiofeed.feedparser import validators

Explicit = Annotated[
    bool,
    BeforeValidator(
        functools.partial(
            validators.one_of,
            values=("yes", "clean"),
        )
    ),
]

Complete = Annotated[
    bool,
    BeforeValidator(
        functools.partial(
            validators.one_of,
            values=("yes",),
        )
    ),
]


AudioMimeType = Annotated[str, BeforeValidator(validators.audio_mime_type)]

Duration = Annotated[str | None, BeforeValidator(validators.duration)]

Language = Annotated[str, BeforeValidator(validators.language)]

PgInteger = Annotated[int | None, BeforeValidator(validators.pg_integer)]

PubDate = Annotated[datetime, BeforeValidator(validators.pub_date)]

Url = Annotated[str | None, BeforeValidator(validators.url)]


class Item(BaseModel):
    """Individual item or episode in RSS or Atom podcast feed."""

    guid: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)

    categories: list[str] = Field(default_factory=list)

    description: str = ""
    keywords: str = ""

    pub_date: PubDate

    media_url: str
    media_type: AudioMimeType

    website: Url | None = None

    explicit: Explicit = False

    length: PgInteger | None = None
    duration: Duration = None

    season: PgInteger | None = None
    episode: PgInteger | None = None

    episode_type: str = "full"

    cover_url: Url | None = None

    @field_validator("media_url", mode="before")
    @classmethod
    def validate_media_url(cls, value: Any) -> str:
        """Validates media url."""
        if (url := validators.url(value)) is None:
            raise ValueError("media_url cannot be None")
        return url

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

    pub_date: datetime | None = None

    language: str = "en"
    website: str | None = None
    cover_url: str | None = None

    funding_text: str = ""
    funding_url: str | None = None

    explicit: bool = False
    complete: bool = False

    items: list[Item]

    categories: list[str] = Field(default_factory=list)

    @field_validator("explicit", mode="before")
    @classmethod
    def validate_explicit(cls, value: Any) -> bool:
        """Validates explicit."""
        return validators.explicit(value)

    @field_validator("complete", mode="before")
    @classmethod
    def validate_complete(cls, value: Any) -> bool:
        """Validates complete."""
        return validators.complete(value)

    @field_validator("language", mode="after")
    @classmethod
    def validate_language(cls, value: Any) -> str:
        """Validates language."""
        return validators.language(value)

    @field_validator("cover_url", mode="after")
    @classmethod
    def validate_cover_url(cls, value: Any) -> str | None:
        """Validates cover url."""
        return validators.url(value)

    @field_validator("website", mode="after")
    @classmethod
    def validate_website(cls, value: Any) -> str | None:
        """Validates website."""
        return validators.url(value)

    @field_validator("funding_url", mode="after")
    @classmethod
    def validate_funding_url(cls, value: Any) -> str | None:
        """Validates funding url."""
        return validators.url(value)

    @model_validator(mode="after")
    def validate_pub_date(self) -> Feed:
        """Set default pub date based on max items pub date."""
        self.pub_date = max(item.pub_date for item in self.items)
        return self
