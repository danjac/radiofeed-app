from __future__ import annotations

import dataclasses

from datetime import datetime
from typing import Generator

import lxml.etree

from radiofeed.podcasts.parsers import converters, xml_parser

NAMESPACES: dict[str, str] = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "media": "http://search.yahoo.com/mrss/",
    "podcast": "https://podcastindex.org/namespace/1.0",
}


class RssParserError(ValueError):
    ...


@dataclasses.dataclass(frozen=True)
class Item:

    guid: str
    title: str
    pub_date: datetime

    media_url: str | None
    media_type: str

    link: str | None = None
    explicit: bool = False
    length: int | None = None
    season: int | None = None
    episode: int | None = None
    cover_url: str | None = None

    episode_type: str = ""
    duration: str = ""
    description: str = ""
    keywords: str = ""


@dataclasses.dataclass(frozen=True)
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
    items: list[Item] = dataclasses.field(default_factory=list)

    @property
    def latest_pub_date(self) -> datetime | None:
        try:
            return max([item.pub_date for item in self.items])
        except ValueError:
            return None


def parse_rss(content: bytes) -> Feed:

    try:

        feed = parse_feed(next(xml_parser.iterparse(content, "channel")))

        if not feed.items:
            raise ValueError("no items in RSS feed")

        return feed

    except (StopIteration, ValueError, lxml.etree.XMLSyntaxError) as e:
        raise RssParserError from e


def parse_feed(channel: lxml.etree.Element) -> Feed:
    with xml_parser.xpath(channel, NAMESPACES) as xpath:
        return Feed(
            title=xpath.first("title/text()", required=True),
            language=xpath.first(
                "language/text()",
                converter=converters.language,
                default="en",
            ),
            explicit=xpath.first(
                "itunes:explicit/text()",
                converter=converters.explicit,
                default=False,
            ),
            cover_url=xpath.first(
                "itunes:image/@href",
                "image/url/text()",
                converter=converters.url,
                default=None,
            ),
            link=xpath.first(
                "link/text()",
                converter=converters.url,
                default=None,
            ),
            funding_url=xpath.first(
                "podcast:funding/@url",
                converter=converters.url,
                default=None,
            ),
            funding_text=xpath.first("podcast:funding/text()"),
            description=xpath.first(
                "description/text()",
                "itunes:summary/text()",
            ),
            owner=xpath.first(
                "itunes:author/text()",
                "itunes:owner/itunes:name/text()",
            ),
            complete=xpath.first(
                "itunes:complete/text()",
                converter=converters.boolean,
                default=False,
            ),
            categories=xpath.all("//itunes:category/@text"),
            items=list(parse_items(channel)),
        )


def parse_items(channel: lxml.etree.Element) -> Generator[Item, None, None]:
    for item in channel.iterfind("item"):
        try:
            yield parse_item(item)
        except ValueError:
            continue


def parse_item(item: lxml.etree.Element) -> Item:
    with xml_parser.xpath(item, NAMESPACES) as xpath:
        return Item(
            guid=xpath.first("guid/text()", required=True),
            title=xpath.first("title/text()", required=True),
            pub_date=xpath.first(
                "pubDate/text()",
                "pubdate/text()",
                converter=converters.pub_date,
                required=True,
            ),
            cover_url=xpath.first(
                "itunes:image/@href",
                converter=converters.url,
                default=None,
            ),
            link=xpath.first(
                "link/text()",
                converter=converters.url,
                default=None,
            ),
            explicit=xpath.first(
                "itunes:explicit/text()",
                converter=converters.explicit,
                default=False,
            ),
            media_url=xpath.first(
                "enclosure//@url",
                "media:content//@url",
                converter=converters.url,
                required=True,
            ),
            media_type=xpath.first(
                "enclosure//@type",
                "media:content//@type",
                converter=converters.audio,
                required=True,
            ),
            length=xpath.first(
                "enclosure//@length",
                "media:content//@fileSize",
                converter=converters.integer,
                default=None,
            ),
            episode=xpath.first(
                "itunes:episode/text()",
                converter=converters.integer,
                default=None,
            ),
            season=xpath.first(
                "itunes:season/text()",
                converter=converters.integer,
                default=None,
            ),
            description=xpath.first(
                "content:encoded/text()",
                "description/text()",
                "itunes:summary/text()",
            ),
            duration=xpath.first(
                "itunes:duration/text()",
                converter=converters.duration,
            ),
            episode_type=xpath.first("itunes:episodetype/text()", default="full"),
            keywords=" ".join(xpath.all("category/text()")),
        )
