import functools
import io
from collections.abc import Iterator
from typing import Final

import lxml.etree

from radiofeed.feedparser.exceptions import InvalidRSSError
from radiofeed.feedparser.models import Feed, Item


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
        self._xpaths: dict[str, lxml.etree.XPath] = {}

    def parse(self, content: bytes) -> Feed:
        """Parse content into Feed instance."""

        try:
            return self._parse_feed(next(self._parse_content(content)))
        except StopIteration as exc:
            raise InvalidRSSError("<channel /> not found in RSS document") from exc

    def _parse_content(self, content: bytes) -> lxml.etree.Element:
        for _, element in lxml.etree.iterparse(
            io.BytesIO(content),
            tag="rss",
            encoding="utf-8",
            no_network=True,
            resolve_entities=False,
            recover=True,
            events=("end",),
        ):
            yield from self._iterparse(element, "channel")

    def _parse_feed(self, channel: lxml.etree.Element) -> Feed:
        try:
            return Feed(
                complete=self._parse(channel, "itunes:complete/text()"),
                cover_url=self._parse(
                    channel, "itunes:image/@href", "image/url/text()"
                ),
                description=self._parse(
                    channel,
                    "description/text()",
                    "itunes:summary/text()",
                ),
                funding_text=self._parse(channel, "podcast:funding/text()"),
                funding_url=self._parse(channel, "podcast:funding/@url"),
                explicit=self._parse(channel, "itunes:explicit/text()"),
                language=self._parse(channel, "language/text()"),
                website=self._parse(channel, "link/text()"),
                title=self._parse(channel, "title/text()"),  # type: ignore[arg-type]
                categories=list(
                    self._iterparse(
                        channel,
                        "//googleplay:category/@text",
                        "//itunes:category/@text",
                        "//media:category/@label",
                        "//media:category/text()",
                    )
                ),
                owner=self._parse(
                    channel,
                    "itunes:author/text()",
                    "itunes:owner/itunes:name/text()",
                ),
                items=list(self._parse_items(channel)),
            )
        except (TypeError, ValueError) as exc:
            raise InvalidRSSError from exc

    def _parse_items(self, channel: lxml.etree.Element) -> Iterator[Item]:
        for item in self._iterparse(channel, "item"):
            try:
                yield self._parse_item(item)
            except (TypeError, ValueError):
                continue

    def _parse_item(self, item: lxml.etree.Element) -> Item:
        return Item(
            categories=list(
                self._iterparse(
                    item,
                    "//itunes:category/@text",
                )
            ),
            description=self._parse(
                item,
                "content:encoded/text()",
                "description/text()",
                "itunes:summary/text()",
            ),
            cover_url=self._parse(item, "itunes:image/@href"),
            duration=self._parse(item, "itunes:duration/text()"),
            episode=self._parse(item, "itunes:episode/text()"),
            episode_type=self._parse(item, "itunes:episodetype/text()"),
            explicit=self._parse(item, "itunes:explicit/text()"),
            guid=self._parse(
                item,
                "guid/text()",
                "atom:id/text()",
                "link/text()",
            ),  # type: ignore[arg-type]
            length=self._parse(item, "enclosure//@length", "media:content//@fileSize"),
            website=self._parse(item, "link/text()"),
            media_type=self._parse(
                item,
                "enclosure//@type",
                "media:content//@type",
            ),  # type: ignore[arg-type]
            media_url=self._parse(
                item,
                "enclosure//@url",
                "media:content//@url",
            ),  # type: ignore[arg-type]
            pub_date=self._parse(item, "pubDate/text()", "pubdate/text()"),
            season=self._parse(item, "itunes:season/text()"),
            title=self._parse(item, "title/text()"),  # type: ignore[arg-type]
        )

    def _iterparse(self, element: lxml.etree.Element, *paths) -> Iterator:
        for path in paths:
            yield from self._xpath(path)(element)

    def _parse(self, element: lxml.etree.Element, *paths) -> str | None:
        try:
            return next(self._iterparse(element, *paths))
        except StopIteration:
            return None

    def _xpath(self, path: str) -> lxml.etree.XPath:
        if path in self._xpaths:
            return self._xpaths[path]

        xpath = self._xpaths[path] = lxml.etree.XPath(path, namespaces=self._NAMESPACES)
        return xpath


@functools.cache
def _rss_parser() -> RSSParser:
    return RSSParser()
