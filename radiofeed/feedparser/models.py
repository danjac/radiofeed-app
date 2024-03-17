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

    items: list[Item]
    pub_date: datetime | None = None

    language: Language = "en"
    website: Url | None = None
    cover_url: Url | None = None

    funding_text: str = ""
    funding_url: Url | None = None

    explicit: Explicit = False
    complete: Complete = False

    categories: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_pub_date(self) -> Feed:
        """Set default pub date based on number of items."""
        self.pub_date = max(item.pub_date for item in self.items)
        return self
