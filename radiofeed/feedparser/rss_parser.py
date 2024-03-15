import functools
import itertools
from collections.abc import Iterator

import bs4

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

    def parse(self, content: bytes) -> Feed:
        """Parses content of RSS document."""
        soup = bs4.BeautifulSoup(content, features="xml")

        if channel := soup.find("channel"):
            return self._parse_feed(channel)

        raise InvalidRSSError("<channel /> not found in RSS document")

    def _parse_feed(self, channel: bs4.element.Tag) -> Feed:
        try:
            return Feed(
                items=list(self._parse_items(channel)),
                categories=list(self._parse_categories(channel)),
                owner=self._parse_owner(channel),
                complete=self._parse(channel, "itunes:complete"),
                cover_url=self._parse(channel, "itunes:image", attr="href")
                or self._parse(channel, "image/url"),
                description=self._parse(channel, "description", "itunes:summary"),
                explicit=self._parse(channel, "itunes:explicit"),
                language=self._parse(channel, "language"),
                website=self._parse(channel, "link"),
                title=self._parse(channel, "title"),  # type: ignore[arg-type]
            )
        except (TypeError, ValueError) as exc:
            raise InvalidRSSError from exc

    def _parse_owner(self, channel: bs4.element.Tag) -> str | None:
        if author := self._parse(channel, "author"):
            return author

        if owner := channel.find("itunes:owner"):
            return self._parse(owner, "itunes:name")

        return None

    def _parse_categories(self, parent: bs4.element.Tag) -> Iterator[str]:
        yield from itertools.chain(
            self._iterparse(parent, "category", attr="text"),
            self._iterparse(parent, "media:category", attr="label"),
            self._iterparse(parent, "media:category"),
            *(
                self._parse_categories(category)
                for category in parent.find_all("itunes:category")
            ),
        )

    def _parse_items(self, channel: bs4.element.Tag) -> Iterator[Item]:
        for item in channel.find_all("item"):
            try:
                yield Item(
                    categories=list(self._iterparse(item, "category")),
                    cover_url=self._parse(item, "itunes:image", attr="href"),
                    website=self._parse(item, "link"),
                    description=self._parse(
                        item, "content:encoded", "description", "itunes:summary"
                    ),
                    duration=self._parse(item, "itunes:duration"),
                    episode=self._parse(item, "itunes:episode"),
                    episode_type=self._parse(item, "itunes:episodetype"),
                    season=self._parse(item, "itunes:season"),
                    explicit=self._parse(item, "itunes:explicit"),
                    length=self._parse(item, "enclosure", attr="length")
                    or self._parse(item, "media:content", attr="fileSize"),
                    media_type=self._parse(
                        item, "enclosure", "media:content", attr="type"
                    ),  # type: ignore[arg-type]
                    media_url=self._parse(
                        item, "enclosure", "media:content", attr="url"
                    ),  # type: ignore[arg-type]
                    pub_date=self._parse(item, "pubDate", "pubdate"),
                    title=self._parse(item, "title"),  # type: ignore[arg-type]
                    guid=self._parse(item, "guid", "atom:id")
                    or self._parse(item, "link"),  # type: ignore[arg-type]
                )

            except (TypeError, ValueError):
                continue

    def _iterparse(
        self, parent: bs4.element.Tag, *names: str, attr: str | None = None
    ) -> Iterator[str]:
        for element in parent.find_all(list(names), recursive=False):
            if value := self._parse_value(element, attr):
                yield value

    def _parse(
        self, parent: bs4.element.Tag, *names: str, attr: str | None = None
    ) -> str | None:
        try:
            return next(self._iterparse(parent, *names, attr=attr))
        except StopIteration:
            return None

    def _parse_value(
        self, element: bs4.element.Tag, attr: str | None = None
    ) -> str | None:
        if attr and (value := element.get(attr)):
            return value.strip()
        if element.text:
            return element.text.strip()
        return None


@functools.cache
def _rss_parser() -> RSSParser:
    return RSSParser()
