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

    soup = bs4.BeautifulSoup(content, features="xml")

    if channel := soup.find("channel"):
        return _parse_feed(channel)

    raise InvalidRSSError("<channel /> not found in RSS document")


def _parse_feed(channel: bs4.element.Tag) -> Feed:
    try:
        return Feed(
            items=list(_parse_items(channel)),
            categories=list(_parse_categories(channel)),
            owner=_parse_owner(channel),
            complete=_find(channel, "itunes:complete"),
            cover_url=_find(channel, "itunes:image", attr="href")
            or _find(channel, "image/url"),
            description=_find(channel, "description", "itunes:summary"),
            explicit=_find(channel, "itunes:explicit"),
            language=_find(channel, "language"),
            website=_find(channel, "link"),
            title=_find(channel, "title") or "",
        )
    except (TypeError, ValueError) as exc:
        raise InvalidRSSError from exc


def _parse_owner(channel: bs4.element.Tag) -> str | None:
    if author := _find(channel, "author"):
        return author

    if owner := channel.find("itunes:owner"):
        return _find(owner, "itunes:name")

    return None


def _parse_categories(parent: bs4.element.Tag) -> Iterator[str]:
    yield from itertools.chain(
        _findall(parent, "category", attr="text"),
        _findall(parent, "media:category", attr="label"),
        _findall(parent, "media:category"),
        *(
            _parse_categories(category)
            for category in parent.find_all("itunes:category")
        ),
    )


def _parse_items(channel: bs4.element.Tag) -> Iterator[Item]:
    for item in channel.find_all("item"):
        try:
            yield _parse_item(item)
        except (TypeError, ValueError):
            continue


def _parse_item(item: bs4.element.Tag) -> Item:
    return Item(
        categories=list(_findall(item, "category")),
        cover_url=_find(item, "itunes:image", attr="href"),
        website=_find(item, "link"),
        description=_find(item, "content:encoded", "description", "itunes:summary"),
        duration=_find(item, "itunes:duration"),
        episode=_find(item, "itunes:episode"),
        episode_type=_find(item, "itunes:episodetype"),
        explicit=_find(item, "itunes:explicit"),
        guid=_find(item, "guid", "atom:id", "link") or "",
        length=_find(item, "enclosure", attr="length")
        or _find(item, "media:content", attr="fileSize"),
        media_type=_find(item, "enclosure", "media:content", attr="type") or "",
        media_url=_find(item, "enclosure", "media:content", attr="url") or "",
        pub_date=_find(item, "pubDate", "pubdate"),
        title=_find(item, "title") or "",
        season=_find(item, "itunes:season"),
    )


def _find(
    parent: bs4.element.Tag,
    *names: str,
    attr: str | None = None,
    default: str | None = None,
) -> str | None:
    for name in names:
        if (element := parent.find(name, recursive=False)) and (
            value := _parse_value(element, attr)
        ):
            return value
    return default


def _findall(
    parent: bs4.element.Tag,
    *names: str,
    attr: str | None = None,
) -> Iterator[str]:
    for element in parent.find_all(list(names), recursive=False):
        if value := _parse_value(element, attr):
            yield value


def _parse_value(element: bs4.element.Tag, attr: str | None = None) -> str | None:
    if attr and (value := element.get(attr)):
        return value.strip()
    if element.text:
        return element.text.strip()
    return None
