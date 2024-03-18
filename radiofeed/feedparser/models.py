from __future__ import annotations

import functools
from datetime import datetime  # noqa: TCH003
from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field, model_validator

from radiofeed.feedparser import validators

OptionalUrl = Annotated[str | None, AfterValidator(validators.url)]

Explicit = Annotated[
    bool,
    BeforeValidator(
        functools.partial(validators.one_of, values=("clean", "yes", "true")),
    ),
]

PgInteger = Annotated[int | None, BeforeValidator(validators.pg_integer)]


class Item(BaseModel):
    """Individual item or episode in RSS or Atom podcast feed."""

    guid: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)

    categories: list[str] = Field(default_factory=list)

    description: str = ""
    keywords: str = ""

    pub_date: Annotated[datetime, BeforeValidator(validators.pub_date)]

    media_url: Annotated[
        str,
        AfterValidator(
            functools.partial(validators.url, required=True),
        ),
    ]

    media_type: Annotated[str, AfterValidator(validators.audio_mimetype)]

    cover_url: OptionalUrl = None
    website: OptionalUrl = None

    explicit: Explicit = False

    length: PgInteger = None

    duration: Annotated[str, BeforeValidator(validators.duration)] = ""

    season: PgInteger = None
    episode: PgInteger = None

    episode_type: str = "full"

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

    language: Annotated[str, AfterValidator(validators.language)] = "en"

    website: OptionalUrl = None
    cover_url: OptionalUrl = None

    funding_text: str = ""
    funding_url: OptionalUrl = None

    explicit: Explicit = False

    complete: Annotated[
        bool,
        BeforeValidator(
            functools.partial(
                validators.one_of,
                values=("yes", "true"),
            )
        ),
    ] = False

    items: list[Item]

    categories: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_pub_date(self) -> Feed:
        """Set default pub date based on max items pub date."""
        self.pub_date = max(item.pub_date for item in self.items)
        return self
