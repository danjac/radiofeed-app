from datetime import datetime
from typing import Any

import attrs
from django.utils import timezone

from radiofeed.feedparser import converters, validators
from radiofeed.feedparser.date_parser import parse_date


@attrs.define(kw_only=True, frozen=True)
class Item:
    """Individual item or episode in RSS or Atom podcast feed."""

    guid: str = attrs.field(validator=validators.required)
    title: str = attrs.field(validator=validators.required)

    website: str | None = attrs.field(converter=converters.url, default=None)

    pub_date: datetime = attrs.field(converter=parse_date)  # type: ignore

    media_url: str = attrs.field(validator=validators.url)
    media_type: str = attrs.field(validator=validators.audio)

    explicit: bool = attrs.field(converter=converters.explicit, default=False)

    length: int | None = attrs.field(
        converter=attrs.converters.optional(  # type: ignore
            attrs.converters.pipe(float, int),  # type: ignore
        ),
        default=None,
    )

    season: int | None = attrs.field(
        converter=attrs.converters.optional(  # type: ignore
            attrs.converters.pipe(float, int),  # type: ignore
        ),
        validator=attrs.validators.optional(validators.pg_integer),
        default=None,
    )

    episode: int | None = attrs.field(
        converter=attrs.converters.optional(  # type: ignore
            attrs.converters.pipe(float, int),  # type: ignore
        ),
        validator=attrs.validators.optional(validators.pg_integer),
        default=None,
    )

    cover_url: str | None = attrs.field(converter=converters.url, default=None)

    duration: str = attrs.field(converter=converters.duration, default=None)

    episode_type: str = attrs.field(
        converter=attrs.converters.default_if_none("full"),  # type: ignore
        default=None,
    )

    description: str = attrs.field(
        converter=attrs.converters.default_if_none(""),  # type: ignore
        default=None,
    )

    categories: list[str] = attrs.field(default=attrs.Factory(list))

    keywords: str = attrs.field()

    @pub_date.validator
    def _check_pub_date(self, attr: attrs.Attribute, value: Any) -> None:
        if value is None:
            msg = f"{attr=} cannot be None"
            raise ValueError(msg)
        if value > timezone.now():
            msg = f"{attr=} cannot be in future"
            raise ValueError(msg)

    @keywords.default
    def _default_keywords(self) -> str:
        return " ".join(filter(None, self.categories))


@attrs.define(kw_only=True, frozen=True)
class Feed:
    """RSS or Atom podcast feed."""

    title: str = attrs.field(validator=validators.required)

    owner: str = attrs.field(
        converter=attrs.converters.default_if_none(""),  # type: ignore
        default=None,
    )
    description: str = attrs.field(
        converter=attrs.converters.default_if_none(""),  # type: ignore
        default=None,
    )

    language: str = attrs.field(
        converter=attrs.converters.pipe(  # type: ignore
            attrs.converters.default_if_none("en"),  # type: ignore
            converters.language,
        ),
        default=None,
    )

    website: str | None = attrs.field(converter=converters.url, default=None)

    cover_url: str | None = attrs.field(converter=converters.url, default=None)

    complete: bool = attrs.field(
        converter=attrs.converters.pipe(  # type: ignore
            attrs.converters.default_if_none(False),  # type: ignore
            attrs.converters.to_bool,  # type: ignore
        ),
        default=False,
    )

    explicit: bool = attrs.field(converter=converters.explicit, default=False)

    funding_text: str = attrs.field(
        converter=attrs.converters.default_if_none(""),  # type: ignore
        default=None,
    )

    funding_url: str | None = attrs.field(converter=converters.url, default=None)

    categories: list[str] = attrs.field(default=attrs.Factory(list))

    items: list[Item] = attrs.field(
        default=attrs.Factory(list),
        validator=validators.required,
    )

    pub_date: datetime = attrs.field()

    @pub_date.default
    def _default_pub_date(self) -> datetime:
        return max(item.pub_date for item in self.items)
