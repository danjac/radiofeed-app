from typing import Generator

import lxml.etree

from radiofeed.podcasts.parsers import xml_parser
from radiofeed.podcasts.parsers.models import Feed, Item

NAMESPACES: dict[str, str] = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "media": "http://search.yahoo.com/mrss/",
    "podcast": "https://podcastindex.org/namespace/1.0",
}


class RssParserError(ValueError):
    ...


def parse_rss(content: bytes) -> Feed:

    try:

        return parse_feed(next(xml_parser.iterparse(content, "channel")))

    except (StopIteration, TypeError, ValueError, lxml.etree.XMLSyntaxError) as e:
        raise RssParserError from e


def parse_feed(channel: lxml.etree.Element) -> Feed:
    with xml_parser.xpath(channel, NAMESPACES) as xpath:
        return Feed(
            title=xpath.first("title/text()"),
            language=xpath.first("language/text()"),
            explicit=xpath.first("itunes:explicit/text()"),
            cover_url=xpath.first("itunes:image/@href", "image/url/text()"),
            link=xpath.first("link/text()"),
            funding_url=xpath.first("podcast:funding/@url"),
            funding_text=xpath.first("podcast:funding/text()"),
            complete=xpath.first("itunes:complete/text()"),
            description=xpath.first("description/text()", "itunes:summary/text()"),
            owner=xpath.first(
                "itunes:author/text()", "itunes:owner/itunes:name/text()"
            ),
            categories=list(xpath.iter("//itunes:category/@text")),
            items=list(parse_items(channel)),
        )


def parse_items(channel: lxml.etree.Element) -> Generator[Item, None, None]:
    for item in channel.iterfind("item"):
        try:
            yield parse_item(item)
        except (TypeError, ValueError):
            continue


def parse_item(item: lxml.etree.Element) -> Item:
    with xml_parser.xpath(item, NAMESPACES) as xpath:
        return Item(
            guid=xpath.first("guid/text()"),
            title=xpath.first("title/text()"),
            pub_date=xpath.first("pubDate/text()", "pubdate/text()"),
            cover_url=xpath.first("itunes:image/@href"),
            link=xpath.first("link/text()"),
            explicit=xpath.first("itunes:explicit/text()"),
            duration=xpath.first("itunes:duration/text()"),
            media_url=xpath.first("enclosure//@url", "media:content//@url"),
            media_type=xpath.first("enclosure//@type", "media:content//@type"),
            length=xpath.first("enclosure//@length", "media:content//@fileSize"),
            episode=xpath.first("itunes:episode/text()"),
            season=xpath.first("itunes:season/text()"),
            episode_type=xpath.first("itunes:episodetype/text()", default="full"),
            description=xpath.first(
                "content:encoded/text()", "description/text()", "itunes:summary/text()"
            ),
            keywords=" ".join(xpath.iter("category/text()")),
        )
