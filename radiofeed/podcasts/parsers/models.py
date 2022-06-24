from __future__ import annotations

from datetime import datetime

import attrs

from radiofeed.podcasts.parsers import converters, validators


@attrs.define(kw_only=True, frozen=True)
class Outline:

    title: str = ""
    text: str = ""

    rss: str | None = attrs.field(validator=validators.url, default=None)
    url: str | None = attrs.field(validator=validators.url, default=None)


@attrs.define(kw_only=True, frozen=True)
class Item:

    guid: str = attrs.field(validator=validators.not_empty)
    title: str = attrs.field(validator=validators.not_empty)

    pub_date: datetime = attrs.field(
        converter=converters.pub_date,
        validator=attrs.validators.and_(
            attrs.validators.instance_of(datetime),
            validators.pub_date,
        ),
    )

    media_url: str = attrs.field(
        validator=attrs.validators.and_(
            validators.not_empty,
            validators.url,
        ),
    )

    media_type: str = attrs.field(validator=validators.audio)

    link: str | None = attrs.field(validator=validators.url, default=None)

    explicit: bool = attrs.field(converter=converters.explicit, default=False)

    length: int | None = attrs.field(
        converter=converters.int_or_none,
        default=None,
    )

    season: int | None = attrs.field(
        converter=converters.int_or_none,
        validator=validators.pg_integer,
        default=None,
    )

    episode: int | None = attrs.field(
        converter=converters.int_or_none,
        validator=validators.pg_integer,
        default=None,
    )

    cover_url: str | None = attrs.field(validator=validators.url, default=None)
    duration: str = attrs.field(converter=converters.duration, default="")

    episode_type: str = "full"
    description: str = ""
    keywords: str = ""


@attrs.define(kw_only=True, frozen=True)
class Feed:

    title: str = attrs.field(validator=validators.not_empty)

    owner: str = ""
    description: str = ""

    language: str = attrs.field(
        converter=converters.language_code,
        validator=validators.language_code,
        default="en",
    )

    link: str | None = attrs.field(validator=validators.url, default=None)
    cover_url: str | None = attrs.field(validator=validators.url, default=None)

    complete: bool = attrs.field(converter=converters.complete, default=False)
    explicit: bool = attrs.field(converter=converters.explicit, default=False)

    funding_text: str = ""
    funding_url: str | None = attrs.field(validator=validators.url, default=None)

    categories: list[str] = attrs.field(default=attrs.Factory(list))

    items: list[Item] = attrs.field(
        default=attrs.Factory(list),
        validator=validators.not_empty,
    )

    @property
    def pub_date(self) -> datetime:
        return max([item.pub_date for item in self.items])
