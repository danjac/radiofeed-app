from __future__ import annotations

import functools

from collections.abc import Iterator

import lxml.etree  # nosec

from radiofeed.feedparser.exceptions import InvalidRSS
from radiofeed.feedparser.models import Feed, Item
from radiofeed.feedparser.xpath_parser import XPathParser


def parse_rss(content: bytes) -> Feed:
    """Parses RSS or Atom feed and returns the feed details and individual episodes.

    Args:
        content: the body of the RSS or Atom feed

    Raises:
        InvalidRSS: if XML content is unparseable, or the feed is otherwise invalid or empty
    """
    parser = _xpath_parser()
    try:
        return _parse_feed(parser, next(parser.iterparse(content, "rss", "channel")))
    except StopIteration as e:
        raise InvalidRSS("Document does not contain <channel /> element") from e
    except lxml.etree.XMLSyntaxError as e:
        raise InvalidRSS from e


def _parse_feed(parser: XPathParser, channel: lxml.etree.Element) -> Feed:
    """Parse a RSS XML feed."""
    try:
        return Feed(
            items=list(_parse_items(parser, channel)),
            categories=parser.aslist(
                channel,
                "//googleplay:category/@text",
                "//itunes:category/@text",
                "//media:category/@label",
                "//media:category/text()",
            ),
            **parser.asdict(
                channel,
                complete="itunes:complete/text()",
                cover_url=("itunes:image/@href", "image/url/text()"),
                description=("description/text()", "itunes:summary/text()"),
                explicit="itunes:explicit/text()",
                funding_text="podcast:funding/text()",
                funding_url="podcast:funding/@url",
                language="language/text()",
                link="link/text()",
                websub_hub="atom:link[@rel='hub']/@href",
                websub_topic="atom:link[@rel='self']/@href",
                owner=(
                    "itunes:author/text()",
                    "itunes:owner/itunes:name/text()",
                ),
                title="title/text()",  # type: ignore
            ),
        )
    except (TypeError, ValueError) as e:
        raise InvalidRSS from e
    finally:
        channel.clear()


def _parse_items(parser: XPathParser, channel: lxml.etree.Element) -> Iterator[Item]:
    for item in parser.findall(channel, "item"):
        try:
            yield Item(
                categories=parser.aslist(item, "category/text()"),
                **parser.asdict(
                    item,
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
            continue
        finally:
            item.clear()


@functools.cache
def _xpath_parser() -> XPathParser:
    return XPathParser(
        {
            "atom": "http://www.w3.org/2005/Atom",
            "content": "http://purl.org/rss/1.0/modules/content/",
            "googleplay": "http://www.google.com/schemas/play-podcasts/1.0",
            "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
            "media": "http://search.yahoo.com/mrss/",
            "podcast": "https://podcastindex.org/namespace/1.0",
        }
    )
