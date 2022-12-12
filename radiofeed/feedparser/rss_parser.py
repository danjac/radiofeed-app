from __future__ import annotations

from typing import Iterator

import lxml.etree  # nosec

from radiofeed.feedparser.exceptions import RssParserError
from radiofeed.feedparser.models import Feed, Item
from radiofeed.feedparser.xml_parser import parse_xml, xpath_parser

_NAMESPACES: dict[str, str] = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "googleplay": "http://www.google.com/schemas/play-podcasts/1.0",
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "media": "http://search.yahoo.com/mrss/",
    "podcast": "https://podcastindex.org/namespace/1.0",
}


def parse_rss(content: bytes) -> Feed:
    """Parses RSS or Atom feed and returns the feed details and individual episodes.

    Args:
        content: the body of the RSS or Atom feed

    Raises:
        RssParserError: if XML content is invalid, or the feed is otherwise invalid or empty
    """
    try:
        channel = next(parse_xml(content, "channel"))
    except StopIteration:
        raise RssParserError("Document does not contain <channel /> element")
    except lxml.etree.XMLSyntaxError as e:
        raise RssParserError from e

    try:
        with xpath_parser(channel, _NAMESPACES) as parser:
            return Feed(
                items=list(_parse_items(channel)),
                categories=parser.to_list(
                    "//googleplay:category/@text",
                    "//itunes:category/@text",
                    "//media:category/@label",
                    "//media:category/text()",
                ),
                **parser.to_dict(
                    complete="itunes:complete/text()",
                    cover_url=("itunes:image/@href", "image/url/text()"),
                    description=("description/text()", "itunes:summary/text()"),
                    explicit="itunes:explicit/text()",
                    funding_text="podcast:funding/text()",
                    funding_url="podcast:funding/@url",
                    language="language/text()",
                    link="link/text()",
                    owner=(
                        "itunes:author/text()",
                        "itunes:owner/itunes:name/text()",
                    ),
                    title="title/text()",  # type: ignore
                ),
            )
    except (TypeError, ValueError) as e:
        raise RssParserError from e


def _parse_items(channel: lxml.etree.Element) -> Iterator[Item]:
    for item in channel.iterfind("item"):
        with xpath_parser(item, _NAMESPACES) as parser:
            try:
                yield Item(
                    categories=parser.to_list("category/text()"),
                    **parser.to_dict(
                        cover_url="itunes:image/@href",
                        description=(
                            "content:encoded/text()",
                            "description/text()",
                            "itunes:summary/text()",
                        ),
                        duration="itunes:duration/text()",
                        episode="itunes:episode/text()",
                        episode_type="itunes:episodetype/text()",
                        explicit="itunes:explicit/text()",
                        guid="guid/text()",
                        length=("enclosure//@length", "media:content//@fileSize"),
                        link="link/text()",
                        media_type=("enclosure//@type", "media:content//@type"),
                        media_url=("enclosure//@url", "media:content//@url"),
                        pub_date=("pubDate/text()", "pubdate/text()"),
                        season="itunes:season/text()",
                        title="title/text()",  # type: ignore
                    ),
                )
            except (TypeError, ValueError):
                # invalid item, just continue
                continue
