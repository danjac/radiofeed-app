import functools
from collections.abc import Iterator
from typing import Final

import lxml.etree
from pydantic import ValidationError

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
            return Feed.parse_obj(
                {
                    "complete": self._parser.value(
                        channel,
                        "itunes:complete/text()",
                        default=False,
                    ),
                    "cover_url": self._parser.value(
                        channel,
                        "itunes:image/@href",
                        "image/url/text()",
                    ),
                    "description": self._parser.value(
                        channel,
                        "description/text()",
                        "itunes:summary/text()",
                        default="",
                    ),
                    "funding_text": self._parser.value(
                        channel,
                        "podcast:funding/text()",
                        default="",
                    ),
                    "funding_url": self._parser.value(channel, "podcast:funding/@url"),
                    "explicit": self._parser.value(
                        channel,
                        "itunes:explicit/text()",
                        default=False,
                    ),
                    "language": self._parser.value(
                        channel,
                        "language/text()",
                        default="en",
                    ),
                    "website": self._parser.value(channel, "link/text()"),
                    "title": self._parser.value(channel, "title/text()"),
                    "categories": list(
                        self._parser.itervalues(
                            channel,
                            ".//googleplay:category/@text",
                            ".//itunes:category/@text",
                            ".//media:category/@label",
                            ".//media:category/text()",
                        )
                    ),
                    "owner": self._parser.value(
                        channel,
                        "itunes:author/text()",
                        "itunes:owner/itunes:name/text()",
                        default="",
                    ),
                    "items": list(self._parse_items(channel)),
                }
            )
        except ValidationError as exc:
            raise InvalidRSSError from exc

    def _parse_items(self, channel: lxml.etree.Element) -> Iterator[Item]:
        for item in self._parser.iterfind(channel, "item"):
            try:
                yield self._parse_item(item)
            except ValidationError:
                continue

    def _parse_item(self, item: lxml.etree.Element) -> Item:
        return Item.parse_obj(
            {
                "categories": list(
                    self._parser.itervalues(
                        item,
                        "//itunes:category/@text",
                    )
                ),
                "description": self._parser.value(
                    item,
                    "content:encoded/text()",
                    "description/text()",
                    "itunes:summary/text()",
                    default="",
                ),
                "cover_url": self._parser.value(item, "itunes:image/@href"),
                "duration": self._parser.value(item, "itunes:duration/text()"),
                "episode": self._parser.value(item, "itunes:episode/text()"),
                "episode_type": self._parser.value(
                    item,
                    "itunes:episodetype/text()",
                    default="full",
                ),
                "explicit": self._parser.value(
                    item,
                    "itunes:explicit/text()",
                    default=False,
                ),
                "guid": self._parser.value(
                    item,
                    "guid/text()",
                    "atom:id/text()",
                    "link/text()",
                ),
                "length": self._parser.value(
                    item, "enclosure/@length", "media:content/@fileSize"
                ),
                "website": self._parser.value(item, "link/text()"),
                "media_type": self._parser.value(
                    item,
                    "enclosure/@type",
                    "media:content/@type",
                ),
                "media_url": self._parser.value(
                    item,
                    "enclosure/@url",
                    "media:content/@url",
                ),
                "pub_date": self._parser.value(
                    item, "pubDate/text()", "pubdate/text()"
                ),
                "season": self._parser.value(item, "itunes:season/text()"),
                "title": self._parser.value(item, "title/text()"),
            }
        )


@functools.cache
def _rss_parser() -> RSSParser:
    return RSSParser()
