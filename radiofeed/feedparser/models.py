from datetime import datetime

import attrs

from django.utils import timezone

from radiofeed.common.utils.dates import parse_date
from radiofeed.feedparser import converters, validators


@attrs.define(kw_only=True, frozen=True)
class Item:
    """Individual item or episode in RSS or Atom podcast feed"""

    guid: str = attrs.field(validator=validators.required)
    title: str = attrs.field(validator=validators.required)

    pub_date: datetime = attrs.field(converter=parse_date)

    media_url: str = attrs.field(validator=validators.url)

    media_type: str = attrs.field(validator=validators.audio)

    link: str | None = attrs.field(converter=converters.url_or_none, default=None)

    explicit: bool = attrs.field(converter=converters.explicit, default=False)

    length: int | None = attrs.field(
        converter=attrs.converters.optional(
            attrs.converters.pipe(float, int),
        ),
        default=None,
    )

    season: int | None = attrs.field(
        converter=attrs.converters.optional(
            attrs.converters.pipe(float, int),
        ),
        validator=attrs.validators.optional(validators.pg_integer),
        default=None,
    )

    episode: int | None = attrs.field(
        converter=attrs.converters.optional(
            attrs.converters.pipe(float, int),
        ),
        validator=attrs.validators.optional(validators.pg_integer),
        default=None,
    )

    cover_url: str | None = attrs.field(converter=converters.url_or_none, default=None)

    duration: str = attrs.field(converter=converters.duration, default=None)

    episode_type: str = attrs.field(
        converter=attrs.converters.default_if_none("full"),
        default=None,
    )

    description: str = attrs.field(
        converter=attrs.converters.default_if_none(""),
        default=None,
    )

    keywords: str = attrs.field(
        converter=attrs.converters.default_if_none(""),
        default=None,
    )

    @pub_date.validator
    def _pub_date_ok(self, attribute, value):
        if value is None:
            raise ValueError("pub_date cannot be null")
        if value > timezone.now():
            raise ValueError("pub_date cannot be in future")


@attrs.define(kw_only=True, frozen=True)
class Feed:
    """RSS or Atom podcast feed"""

    title: str = attrs.field(validator=validators.required)

    owner: str = attrs.field(
        converter=attrs.converters.default_if_none(""),
        default=None,
    )
    description: str = attrs.field(
        converter=attrs.converters.default_if_none(""),
        default=None,
    )

    language: str = attrs.field(
        converter=attrs.converters.pipe(
            attrs.converters.default_if_none("en"),
            lambda value: value[:2],
        ),
        default=None,
    )

    link: str | None = attrs.field(converter=converters.url_or_none, default=None)

    cover_url: str | None = attrs.field(converter=converters.url_or_none, default=None)

    complete: bool = attrs.field(
        converter=attrs.converters.pipe(
            attrs.converters.default_if_none(False),
            attrs.converters.to_bool,
        ),
        default=False,
    )

    explicit: bool = attrs.field(converter=converters.explicit, default=False)

    funding_text: str = attrs.field(
        converter=attrs.converters.default_if_none(""), default=None
    )

    funding_url: str | None = attrs.field(
        converter=converters.url_or_none, default=None
    )

    categories: list[str] = attrs.field(default=attrs.Factory(list))

    items: list[Item] = attrs.field(
        default=attrs.Factory(list),
        validator=validators.required,
    )

    pub_date: datetime | None = attrs.field()

    @pub_date.default
    def _default_pub_date(self):
        return max([item.pub_date for item in self.items])
