import functools
from collections.abc import Iterator
from typing import Final

import lxml.etree

from radiofeed.feedparser.exceptions import InvalidRSSError
from radiofeed.feedparser.models import Feed, Item
from radiofeed.feedparser.xpath_parser import XPathParser


def parse_rss(content: bytes) -> Feed:
    """Parses RSS or Atom feed and returns the feed details and individual episodes.

    Args:
        content: the body of the RSS or Atom feed

    Raises:
        InvalidRSSError: if XML content is unparseable, or the feed is otherwise invalid
        or empty.
    """
    return _rss_parser().parse(content)


class RSSParser:
    """Parses RSS or Atom document."""

    _NAMESPACES: Final = {
        "atom": "http://www.w3.org/2005/Atom",
        "content": "http://purl.org/rss/1.0/modules/content/",
        "googleplay": "http://www.google.com/schemas/play-podcasts/1.0",
        "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
        "media": "http://search.yahoo.com/mrss/",
        "podcast": "https://podcastindex.org/namespace/1.0",
    }

    def __init__(self) -> None:
        self._parser = XPathParser(self._NAMESPACES)

    def parse(self, content: bytes) -> Feed:
        """Parse content into Feed instance."""
        try:
            return self._parse_feed(
                next(self._parser.iterparse(content, "rss", "channel"))
            )
        except (lxml.etree.XMLSyntaxError, StopIteration) as exc:
            raise InvalidRSSError from exc

    def _parse_feed(self, channel: lxml.etree.Element) -> Feed:
        try:
            return Feed(
                complete=self._parser.string(channel, "itunes:complete/text()"),
                cover_url=self._parser.string(
                    channel,
                    "itunes:image/@href",
                    "image/url/text()",
                ),
                description=self._parser.string(
                    channel,
                    "description/text()",
                    "itunes:summary/text()",
                ),
                funding_text=self._parser.string(channel, "podcast:funding/text()"),
                funding_url=self._parser.string(channel, "podcast:funding/@url"),
                explicit=self._parser.string(channel, "itunes:explicit/text()"),
                language=self._parser.string(channel, "language/text()"),
                website=self._parser.string(channel, "link/text()"),
                title=self._parser.string(channel, "title/text()"),  # type: ignore[arg-type]
                categories=list(
                    self._parser.iterstrings(
                        channel,
                        ".//googleplay:category/@text",
                        ".//itunes:category/@text",
                        ".//media:category/@label",
                        ".//media:category/text()",
                    )
                ),
                owner=self._parser.string(
                    channel,
                    "itunes:author/text()",
                    "itunes:owner/itunes:name/text()",
                ),
                items=list(self._parse_items(channel)),
            )
        except (TypeError, ValueError) as exc:
            raise InvalidRSSError from exc

    def _parse_items(self, channel: lxml.etree.Element) -> Iterator[Item]:
        for item in self._parser.iterfind(channel, "item"):
            try:
                yield self._parse_item(item)
            except (TypeError, ValueError):
                continue

    def _parse_item(self, item: lxml.etree.Element) -> Item:
        return Item(
            categories=list(
                self._parser.iterstrings(
                    item,
                    "//itunes:category/@text",
                )
            ),
            description=self._parser.string(
                item,
                "content:encoded/text()",
                "description/text()",
                "itunes:summary/text()",
            ),
            cover_url=self._parser.string(item, "itunes:image/@href"),
            duration=self._parser.string(item, "itunes:duration/text()"),
            episode=self._parser.string(item, "itunes:episode/text()"),
            episode_type=self._parser.string(item, "itunes:episodetype/text()"),
            explicit=self._parser.string(item, "itunes:explicit/text()"),
            guid=self._parser.string(
                item,
                "guid/text()",
                "atom:id/text()",
                "link/text()",
            ),  # type: ignore[arg-type]
            length=self._parser.string(
                item, "enclosure/@length", "media:content/@fileSize"
            ),
            website=self._parser.string(item, "link/text()"),
            media_type=self._parser.string(
                item,
                "enclosure/@type",
                "media:content/@type",
            ),  # type: ignore[arg-type]
            media_url=self._parser.string(
                item,
                "enclosure/@url",
                "media:content/@url",
            ),  # type: ignore[arg-type]
            pub_date=self._parser.string(item, "pubDate/text()", "pubdate/text()"),
            season=self._parser.string(item, "itunes:season/text()"),
            title=self._parser.string(item, "title/text()"),  # type: ignore[arg-type]
        )


@functools.cache
def _rss_parser() -> RSSParser:
    return RSSParser()
