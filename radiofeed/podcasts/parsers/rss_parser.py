from __future__ import annotations

import dataclasses

from datetime import datetime
from typing import Generator

import lxml.etree

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone

from radiofeed.podcasts.parsers.date_parser import parse_date
from radiofeed.podcasts.parsers.xml_parser import XPathFinder, iterparse

NAMESPACES: dict[str, str] = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "media": "http://search.yahoo.com/mrss/",
    "podcast": "https://podcastindex.org/namespace/1.0",
}


_validate_url = URLValidator(["http", "https"])


class RssParserError(ValueError):
    ...


@dataclasses.dataclass
class Item:

    guid: str
    title: str
    media_url: str | None
    media_type: str

    link: str | None = None
    pub_date: datetime | None = None
    explicit: bool = False

    length: int | None = None
    season: int | None = None
    episode: int | None = None
    cover_url: str | None = None

    episode_type: str = ""
    duration: str = ""
    description: str = ""
    keywords: str = ""


@dataclasses.dataclass
class Feed:

    title: str
    language: str

    link: str | None = None
    cover_url: str | None = None
    funding_text: str = ""
    funding_url: str | None = None
    owner: str = ""
    description: str = ""
    complete: bool = False
    explicit: bool = False

    categories: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Result:
    feed: Feed
    items: list[Item]

    @property
    def latest_pub_date(self):
        return max([item.pub_date for item in self.items if item.pub_date])


def parse_rss(content: bytes) -> Result:

    try:
        for element in iterparse(content):
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


def parse_channel(channel: lxml.etree.Element, namespaces: dict[str, str]) -> Result:
    try:
        feed = parse_feed(XPathFinder(channel, namespaces))
    except (TypeError, ValueError) as e:
        raise RssParserError from e
    if not (items := [*parse_items(channel, namespaces)]):
        raise RssParserError("no items found in RSS feed")
    return Result(feed=feed, items=items)


def parse_feed(finder: XPathFinder) -> Feed:
    return Feed(
        title=finder.first("title/text()", required=True),
        link=parse_url(finder.first("link/text()")),
        language=finder.first("language/text()", default="en")[:2],
        explicit=parse_explicit(finder.first("itunes:explicit/text()")),
        cover_url=parse_url(finder.first("itunes:image/@href", "image/url/text()")),
        funding_url=parse_url(finder.first("podcast:funding/@url")),
        funding_text=finder.first("podcast:funding/text()"),
        description=finder.first(
            "description/text()",
            "itunes:summary/text()",
        ),
        owner=finder.first(
            "itunes:author/text()",
            "itunes:owner/itunes:name/text()",
        ),
        complete=finder.first("itunes:complete/text()").casefold() == "yes",
        categories=finder.all("//itunes:category/@text"),
    )


def parse_items(
    channel: lxml.etree.Element, namespaces: dict[str, str]
) -> Generator[Item, None, None]:

    for item in channel.iterfind("item"):

        try:
            yield parse_item(XPathFinder(item, namespaces))

        except ValueError:
            continue


def parse_item(finder: XPathFinder) -> Item:
    return Item(
        guid=finder.first("guid/text()", required=True),
        title=finder.first("title/text()", required=True),
        pub_date=parse_pub_date(finder.first("pubDate/text()", required=True)),
        link=parse_url(finder.first("link/text()")),
        media_url=parse_url(
            finder.first(
                "enclosure//@url",
                "media:content//@url",
                required=True,
            ),
            raises=True,
        ),
        media_type=parse_audio(
            finder.first(
                "enclosure//@type",
                "media:content//@type",
                required=True,
            )
        ),
        length=parse_int(
            finder.first(
                "enclosure//@length",
                "media:content//@fileSize",
            )
        ),
        explicit=parse_explicit(finder.first("itunes:explicit/text()")),
        cover_url=parse_url(finder.first("itunes:image/@href")),
        episode=parse_int(finder.first("itunes:episode/text()")),
        season=parse_int(finder.first("itunes:season/text()")),
        description=finder.first(
            "content:encoded/text()",
            "description/text()",
            "itunes:summary/text()",
        ),
        duration=parse_duration(finder.first("itunes:duration/text()")),
        episode_type=finder.first("itunes:episodetype/text()", default="full"),
        keywords=" ".join(finder.all("category/text()")),
    )


def parse_audio(value: str) -> str:
    if not value.startswith("audio/"):
        raise ValueError("not a valid audio enclosure")
    return value


def parse_pub_date(value: str) -> datetime:
    if not (pub_date := parse_date(value)) or pub_date > timezone.now():
        raise ValueError("not a valid pub date")
    return pub_date


def parse_explicit(value: str) -> bool:
    return value.casefold() in ("clean", "yes")


def parse_url(value: str, raises: bool = False) -> str | None:
    try:
        _validate_url(value)
        return value
    except ValidationError as e:
        if raises:
            raise ValueError from e
    return None


def parse_int(value: str) -> int | None:

    try:
        if (result := int(value)) in range(-2147483648, 2147483647):
            return result
    except ValueError:
        pass
    return None


def parse_duration(value: str) -> str:
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
