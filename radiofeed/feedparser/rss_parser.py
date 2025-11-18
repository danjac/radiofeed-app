import contextlib
import functools
from collections.abc import Iterator
from typing import Final

from pydantic import ValidationError

from radiofeed.feedparser.exceptions import InvalidRSSError
from radiofeed.feedparser.models import Feed, Item
from radiofeed.feedparser.xpath_parser import OptionalXmlElement, XPathParser


def parse_rss(content: bytes) -> Feed:
    """Parses RSS or Atom feed and returns the feed details and individual episodes.

    Args:
        content: the body of the RSS or Atom feed

    Raises:
        InvalidRSSError: if XML content is unparseable, or the feed is otherwise invalid
        or empty.
    """
    return _rss_parser().parse(content)


class _RSSParser:
    """Parses RSS or Atom document."""

    _NAMESPACES: Final = (
        ("atom", "http://www.w3.org/2005/Atom"),
        ("content", "http://purl.org/rss/1.0/modules/content/"),
        ("googleplay", "http://www.google.com/schemas/play-podcasts/1.0"),
        ("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd"),
        ("media", "http://search.yahoo.com/mrss/"),
        ("podcast", "https://podcastindex.org/namespace/1.0"),
    )

    def __init__(self) -> None:
        self._parser = XPathParser(self._NAMESPACES)

    def parse(self, content: bytes) -> Feed:
        """Parse content into Feed instance."""
        if (channel := self._parser.find(content, "rss", "channel")) is None:
            raise InvalidRSSError("No <channel /> element found in RSS feed.")
        return self._parse_feed(channel)

    def _parse_feed(self, channel: OptionalXmlElement) -> Feed:
        try:
            return Feed.model_validate(
                {
                    "complete": self._parser.value(
                        channel,
                        "itunes:complete/text()",
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
                    ),
                    "canonical_url": self._parser.value(
                        channel,
                        "itunes:new-feed-url/text()",
                        "atom:link[@rel='self']/@href",
                    ),
                    "funding_text": self._parser.value(
                        channel,
                        "podcast:funding/text()",
                    ),
                    "funding_url": self._parser.value(channel, "podcast:funding/@url"),
                    "explicit": self._parser.value(
                        channel,
                        "itunes:explicit/text()",
                    ),
                    "language": self._parser.value(
                        channel,
                        "language/text()",
                    ),
                    "podcast_type": self._parser.value(channel, "itunes:type/text()"),
                    "website": self._parser.value(channel, "link/text()"),
                    "keywords": self._parser.value(channel, "itunes:keywords/text()"),
                    "title": self._parser.value(channel, "title/text()"),
                    "categories": self._parser.itervalues(
                        channel,
                        ".//googleplay:category/@text",
                        ".//itunes:category/@text",
                        ".//media:category/@label",
                        ".//media:category/text()",
                    ),
                    "owner": self._parser.value(
                        channel,
                        "itunes:author/text()",
                        "itunes:owner/itunes:name/text()",
                    ),
                    "items": self._parse_items(channel),
                }
            )
        except ValidationError as exc:
            raise InvalidRSSError from exc

    def _parse_items(self, channel: OptionalXmlElement) -> Iterator[Item]:
        for item in self._parser.iterfind(channel, "item"):
            with contextlib.suppress(ValidationError):
                yield self._parse_item(item)

    def _parse_item(self, item: OptionalXmlElement) -> Item:
        return Item.model_validate(
            {
                "description": self._parser.value(
                    item,
                    "content:encoded/text()",
                    "description/text()",
                    "itunes:summary/text()",
                ),
                "cover_url": self._parser.value(item, "itunes:image/@href"),
                "duration": self._parser.value(item, "itunes:duration/text()"),
                "episode": self._parser.value(item, "itunes:episode/text()"),
                "episode_type": self._parser.value(
                    item,
                    "itunes:episodeType/text()",
                ),
                "explicit": self._parser.value(
                    item,
                    "itunes:explicit/text()",
                ),
                "guid": self._parser.value(
                    item,
                    "guid/text()",
                    "atom:id/text()",
                    "link/text()",
                ),
                "file_size": self._parser.value(
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
def _rss_parser() -> _RSSParser:
    return _RSSParser()
