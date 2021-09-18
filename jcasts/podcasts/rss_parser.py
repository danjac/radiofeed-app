import io

from datetime import datetime
from typing import Optional

import attr
import lxml.etree

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone

from jcasts.podcasts.date_parser import parse_date

NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "podcast": "https://podcastindex.org/namespace/1.0",
}


_validate_url = URLValidator(["http", "https"])


def is_explicit(value):
    return value in ("clean", "yes")


def int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def url_or_none(value):
    try:
        _validate_url(value)
        return value
    except ValidationError:
        return None


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


def is_url(inst, attr, value):
    try:
        _validate_url(value)
    except ValidationError as e:
        raise ValueError from e


def not_empty(inst, attr, value):
    if not value:
        raise ValueError(f"{attr} is empty")


class RssParserError(ValueError):
    ...


@attr.s(kw_only=True)
class Item:

    guid: str = attr.ib(validator=not_empty)
    title: str = attr.ib(validator=not_empty)

    pub_date: datetime = attr.ib(converter=parse_date)

    media_url: str = attr.ib(validator=is_url)
    media_type: str = attr.ib()

    explicit: bool = attr.ib(converter=is_explicit)

    length: Optional[int] = attr.ib(default=None, converter=int_or_none)
    season: Optional[int] = attr.ib(default=None, converter=int_or_none)
    episode: Optional[int] = attr.ib(default=None, converter=int_or_none)

    cover_url: Optional[str] = attr.ib(default=None, converter=url_or_none)

    episode_type: str = attr.ib(default="full")
    duration: str = attr.ib(default="", converter=duration)

    description: str = attr.ib(default="")
    keywords: str = attr.ib(default="", converter=lambda value: " ".join(value or []))

    @pub_date.validator
    def is_pub_date_ok(self, attr, value):
        if not value or value > timezone.now():
            raise ValueError("not a valid pub date")

    @media_type.validator
    def is_audio(self, attr, value):
        if not (value or "").startswith("audio/"):
            raise ValueError("not a valid audio enclosure")


@attr.s(kw_only=True)
class Feed:

    title: str = attr.ib(validator=not_empty)

    language: str = attr.ib(default="en", converter=lambda value: value[:2])

    link: Optional[str] = attr.ib(default=None, converter=url_or_none)
    hub: Optional[str] = attr.ib(default=None, converter=url_or_none)
    cover_url: Optional[str] = attr.ib(default=None, converter=url_or_none)

    funding_text: str = attr.ib(default="")
    funding_url: Optional[str] = attr.ib(default=None, converter=url_or_none)

    owner: str = attr.ib(default="")
    description: str = attr.ib(default="")

    explicit: bool = attr.ib(default=False, converter=is_explicit)

    categories: list[str] = attr.ib(default=list)


def parse_rss(content):

    try:
        for _, element in lxml.etree.iterparse(
            io.BytesIO(content),
            encoding="utf-8",
            no_network=True,
            resolve_entities=False,
            recover=True,
            events=("end",),
        ):
            if element.tag == "channel":
                try:
                    return parse_channel(
                        element,
                        namespaces=NAMESPACES | (element.getparent().nsmap or {}),
                    )
                finally:
                    element.clear()

    except lxml.etree.XMLSyntaxError as e:
        raise RssParserError from e

    raise RssParserError("<channel /> not found in RSS feed")


def parse_channel(channel, namespaces):
    try:
        feed = parse_feed(XPathFinder(channel, namespaces))
    except (TypeError, ValueError) as e:
        raise RssParserError from e
    if not (items := [*parse_items(channel, namespaces)]):
        raise RssParserError("no items found in RSS feed")
    return feed, items


def parse_feed(finder):
    return Feed(
        title=finder.find("title/text()"),
        link=finder.find("link/text()", default=""),
        language=finder.find("language/text()", default="en"),
        explicit=finder.find("itunes:explicit/text()"),
        cover_url=finder.find("itunes:image/@href", "image/url/text()"),
        funding_url=finder.find("podcast:funding/@url", default=""),
        funding_text=finder.find("podcast:funding/text()", default=""),
        hub=finder.find(
            "link[@rel='hub']/@href",
            "atom:link[@rel='hub']/@href",
        ),
        description=finder.find(
            "description/text()",
            "itunes:summary/text()",
            default="",
        ),
        owner=finder.find(
            "itunes:author/text()",
            "itunes:owner/itunes:name/text()",
            default="",
        ),
        categories=finder.findall("//itunes:category/@text"),
    )


def parse_items(channel, namespaces):

    for item in channel.iterfind("item"):

        try:
            yield parse_item(XPathFinder(item, namespaces))

        except (ValueError, TypeError):
            pass


def parse_item(finder):
    return Item(
        guid=finder.find("guid/text()"),
        title=finder.find("title/text()"),
        pub_date=finder.find("pubDate/text()"),
        media_url=finder.find("enclosure//@url"),
        media_type=finder.find("enclosure//@type"),
        length=finder.find("enclosure//@length"),
        explicit=finder.find("itunes:explicit/text()"),
        cover_url=finder.find("itunes:image/@href"),
        episode=finder.find("itunes:episode/text()"),
        season=finder.find("itunes:season/text()"),
        description=finder.find(
            "content:encoded/text()",
            "description/text()",
            "itunes:summary/text()",
            default="",
        ),
        duration=finder.find("itunes:duration/text()", default=""),
        episode_type=finder.find("itunes:episodetype/text()", default="full"),
        keywords=finder.findall("category/text()"),
    )


class XPathFinder:
    def __init__(self, element, namespaces=None):
        self.element = element
        self.namespaces = namespaces

    def find(self, *paths, default=None):

        """Find single attribute or text value. Returns
        first matching value."""
        for path in paths:
            try:
                return self.findall(path)[0]
            except IndexError:
                pass
        return default

    def findall(self, path):
        try:
            return [
                value.strip()
                for value in self.element.xpath(path, namespaces=self.namespaces)
            ]
        except UnicodeDecodeError:
            return []
