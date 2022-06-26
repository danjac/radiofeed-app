from datetime import datetime

import attrs

from radiofeed.podcasts.parsers import converters, validators


@attrs.define(kw_only=True, frozen=True)
class Outline:

    title: str = attrs.field(
        converter=attrs.converters.default_if_none(""),
        default=None,
    )

    text: str = attrs.field(
        converter=attrs.converters.default_if_none(""),
        default=None,
    )

    rss: str = attrs.field(validator=validators.url)

    url: str | None = attrs.field(
        validator=attrs.validators.optional(validators.url),
        default=None,
    )


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

    media_url: str = attrs.field(validator=validators.url)

    media_type: str = attrs.field(validator=validators.audio)

    link: str | None = attrs.field(
        validator=attrs.validators.optional(validators.url),
        default=None,
    )

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

    cover_url: str | None = attrs.field(
        validator=attrs.validators.optional(validators.url),
        default=None,
    )

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


@attrs.define(kw_only=True, frozen=True)
class Feed:

    title: str = attrs.field(validator=validators.not_empty)

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
            converters.language_code,
        ),
        validator=validators.language_code,
        default=None,
    )

    link: str | None = attrs.field(
        validator=attrs.validators.optional(validators.url),
        default=None,
    )

    cover_url: str | None = attrs.field(
        validator=attrs.validators.optional(validators.url),
        default=None,
    )

    complete: bool = attrs.field(converter=converters.complete, default=False)
    explicit: bool = attrs.field(converter=converters.explicit, default=False)

    funding_text: str = attrs.field(
        converter=attrs.converters.default_if_none(""), default=None
    )

    funding_url: str | None = attrs.field(
        validator=attrs.validators.optional(validators.url),
        default=None,
    )

    categories: list[str] = attrs.field(default=attrs.Factory(list))

    items: list[Item] = attrs.field(
        default=attrs.Factory(list),
        validator=validators.not_empty,
    )

    pub_date: datetime | None = attrs.field()

    @pub_date.default
    def _default_pub_date(self):
        return max([item.pub_date for item in self.items])
