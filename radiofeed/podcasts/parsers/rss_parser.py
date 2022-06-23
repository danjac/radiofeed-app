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
            title=converters.text(*xpath("title/text()"), required=True),
            language=converters.language(*xpath("language/text()")),
            explicit=converters.explicit(*xpath("itunes:explicit/text()")),
            cover_url=converters.url(
                *xpath(
                    "itunes:image/@href",
                    "image/url/text()",
                ),
            ),
            link=converters.url(*xpath("link/text()")),
            funding_url=converters.url(*xpath("podcast:funding/@url")),
            funding_text=converters.text(*xpath("podcast:funding/text()")),
            description=converters.text(
                *xpath(
                    "description/text()",
                    "itunes:summary/text()",
                )
            ),
            owner=converters.text(
                *xpath(
                    "itunes:author/text()",
                    "itunes:owner/itunes:name/text()",
                )
            ),
            complete=converters.boolean(*xpath("itunes:complete/text()")),
            categories=list(xpath("//itunes:category/@text")),
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
            guid=converters.text(*xpath("guid/text()"), required=True),
            title=converters.text(*xpath("title/text()"), required=True),
            pub_date=converters.pub_date(
                *xpath(
                    "pubDate/text()",
                    "pubdate/text()",
                ),
            ),
            cover_url=converters.url(*xpath("itunes:image/@href")),
            link=converters.url(*xpath("link/text()")),
            media_url=converters.url(
                *xpath(
                    "enclosure//@url",
                    "media:content//@url",
                ),
                required=True,
            ),
            media_type=converters.audio(
                *xpath(
                    "enclosure//@type",
                    "media:content//@type",
                ),
            ),
            length=converters.integer(
                *xpath(
                    "enclosure//@length",
                    "media:content//@fileSize",
                ),
            ),
            explicit=converters.explicit(*xpath("itunes:explicit/text()")),
            episode=converters.integer(*xpath("itunes:episode/text()")),
            season=converters.integer(*xpath("itunes:season/text()")),
            duration=converters.duration(*xpath("itunes:duration/text()")),
            episode_type=converters.text(
                *xpath("itunes:episodetype/text()"),
                default="full",
            ),
            description=converters.text(
                *xpath(
                    "content:encoded/text()",
                    "description/text()",
                    "itunes:summary/text()",
                )
            ),
            keywords=" ".join(xpath("category/text()")),
        )
