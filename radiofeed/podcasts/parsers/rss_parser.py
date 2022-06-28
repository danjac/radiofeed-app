from datetime import datetime

import attrs
import lxml.etree

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone

from radiofeed.podcasts.parsers import date_parser, xml_parser

NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "media": "http://search.yahoo.com/mrss/",
    "podcast": "https://podcastindex.org/namespace/1.0",
}


AUDIO_MIMETYPES = (
    "audio/aac",
    "audio/aacp",
    "audio/basic",
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
    "audio/vnd.wave",
    "audio/wav",
    "audio/wave",
    "audio/x-aac",
    "audio/x-aiff",
    "audio/x-aiff",
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
)


# ensure integer falls within PostgreSQL INTEGER range

pg_integer = attrs.validators.and_(
    attrs.validators.gt(-2147483648),
    attrs.validators.lt(2147483647),
)


_url_validator = URLValidator(["http", "https"])


def not_empty(instance, attr, value):
    if not value:
        raise ValueError(f"{attr=} cannot be empty or None")


def url(instance, attr, value):
    try:
        _url_validator(value)
    except ValidationError as e:
        raise ValueError from e


def explicit(value):
    if value and value.casefold() in ("clean", "yes"):
        return True
    return False


def duration(value):
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
                if v in range(0, 60)
            ]
        )
    except ValueError:
        return ""


@attrs.define(kw_only=True, frozen=True)
class Item:

    guid: str = attrs.field(validator=not_empty)
    title: str = attrs.field(validator=not_empty)

    pub_date: datetime = attrs.field(converter=date_parser.parse_date)

    media_url: str = attrs.field(validator=url)

    media_type: str = attrs.field(validator=attrs.validators.in_(AUDIO_MIMETYPES))

    link: str | None = attrs.field(
        validator=attrs.validators.optional(url),
        default=None,
    )

    explicit: bool = attrs.field(converter=explicit, default=False)

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
        validator=attrs.validators.optional(pg_integer),
        default=None,
    )

    episode: int | None = attrs.field(
        converter=attrs.converters.optional(
            attrs.converters.pipe(float, int),
        ),
        validator=attrs.validators.optional(pg_integer),
        default=None,
    )

    cover_url: str | None = attrs.field(
        validator=attrs.validators.optional(url),
        default=None,
    )

    duration: str = attrs.field(converter=duration, default=None)

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

    title: str = attrs.field(validator=not_empty)

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

    link: str | None = attrs.field(
        validator=attrs.validators.optional(url),
        default=None,
    )

    cover_url: str | None = attrs.field(
        validator=attrs.validators.optional(url),
        default=None,
    )

    complete: bool = attrs.field(
        converter=lambda value: value and value.casefold() == "yes",
        default=False,
    )

    explicit: bool = attrs.field(converter=explicit, default=False)

    funding_text: str = attrs.field(
        converter=attrs.converters.default_if_none(""), default=None
    )

    funding_url: str | None = attrs.field(
        validator=attrs.validators.optional(url),
        default=None,
    )

    categories: list[str] = attrs.field(default=attrs.Factory(list))

    items: list[Item] = attrs.field(
        default=attrs.Factory(list),
        validator=not_empty,
    )

    pub_date: datetime | None = attrs.field()

    @pub_date.default
    def _default_pub_date(self):
        return max([item.pub_date for item in self.items])


class RssParserError(ValueError):
    ...


def parse_rss(content):

    try:

        return parse_feed(next(xml_parser.iterparse(content, "channel")))

    except (StopIteration, TypeError, ValueError, lxml.etree.XMLSyntaxError) as e:
        raise RssParserError from e


def parse_feed(channel):
    with xml_parser.xpath(channel, NAMESPACES) as xpath:
        return Feed(
            title=xpath.first("title/text()"),
            language=xpath.first("language/text()"),
            complete=xpath.first("itunes:complete/text()"),
            explicit=xpath.first("itunes:explicit/text()"),
            cover_url=xpath.first(
                "itunes:image/@href",
                "image/url/text()",
            ),
            link=xpath.first("link/text()"),
            funding_url=xpath.first("podcast:funding/@url"),
            funding_text=xpath.first(
                "podcast:funding/text()",
            ),
            description=xpath.first(
                "description/text()",
                "itunes:summary/text()",
            ),
            owner=xpath.first(
                "itunes:author/text()",
                "itunes:owner/itunes:name/text()",
            ),
            categories=list(xpath.iter("//itunes:category/@text")),
            items=list(parse_items(channel)),
        )


def parse_items(channel):
    for item in channel.iterfind("item"):
        try:
            yield parse_item(item)
        except (TypeError, ValueError):
            continue


def parse_item(item):
    with xml_parser.xpath(item, NAMESPACES) as xpath:
        return Item(
            guid=xpath.first("guid/text()"),
            title=xpath.first("title/text()"),
            pub_date=xpath.first(
                "pubDate/text()",
                "pubdate/text()",
            ),
            media_url=xpath.first(
                "enclosure//@url",
                "media:content//@url",
            ),
            media_type=xpath.first(
                "enclosure//@type",
                "media:content//@type",
            ),
            cover_url=xpath.first("itunes:image/@href"),
            link=xpath.first("link/text()"),
            explicit=xpath.first("itunes:explicit/text()"),
            duration=xpath.first("itunes:duration/text()"),
            length=xpath.first(
                "enclosure//@length",
                "media:content//@fileSize",
            ),
            episode=xpath.first("itunes:episode/text()"),
            season=xpath.first("itunes:season/text()"),
            episode_type=xpath.first("itunes:episodetype/text()"),
            description=xpath.first(
                "content:encoded/text()",
                "description/text()",
                "itunes:summary/text()",
            ),
            keywords=" ".join(xpath.iter("category/text()")),
        )
