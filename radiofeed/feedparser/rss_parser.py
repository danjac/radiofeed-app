import functools
import itertools

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
        return _parse_channel(channel)

    raise InvalidRSSError("<channel /> not found in RSS document")


def _parse_channel(channel):
    find = functools.partial(_find, channel)
    try:
        return Feed(
            items=list(_parse_items(channel)),
            categories=list(_parse_categories(channel)),
            owner=_parse_owner(channel),
            complete=find("itunes:complete"),
            cover_url=find("itunes:image", attr="href") or _find("image/url"),
            description=find("description", "itunes:summary"),
            explicit=find("itunes:explicit"),
            language=find("language"),
            website=find("link"),
            title=find("title"),
        )
    except (TypeError, ValueError) as exc:
        raise InvalidRSSError from exc


def _parse_owner(channel):
    if author := _find(channel, "author"):
        return author

    if owner := channel.find("itunes:owner"):
        return _find(owner, "itunes:name")

    return None


def _parse_categories(parent):
    yield from itertools.chain(
        _findall(parent, "category", attr="text"),
        _findall(parent, "media:category", attr="label"),
        _findall(parent, "media:category"),
    )

    for category in parent.find_all("itunes:category"):
        yield from _parse_categories(category)


def _parse_items(channel):
    for item in channel.find_all("item"):
        try:
            yield _parse_item(item)
        except (TypeError, ValueError):
            continue


def _parse_item(item):
    find = functools.partial(_find, item)
    return Item(
        categories=_findall(item, "category"),
        cover_url=find("itunes:image", attr="href"),
        website=find("link"),
        description=find("content:encoded", "description", "itunes:summary"),
        duration=find("itunes:duration"),
        episode=find("itunes:episode"),
        episode_type=find("itunes:episodetype"),
        explicit=find("itunes:explicit"),
        guid=find("guid", "atom:id", "link"),
        length=find("enclosure", attr="length")
        or _find("media:content", attr="fileSize"),
        media_type=find("enclosure", "media:content", attr="type"),
        media_url=find("enclosure", "media:content", attr="url"),
        pub_date=find("pubDate", "pubdate"),
        title=find("title"),
        season=find("itunes:season"),
    )


def _find(
    parent: bs4.element.Tag,
    *names: str,
    attr: str | None = None,
    recursive=False,
):
    for name in names:
        if element := parent.find(name, recursive=recursive):
            if attr:
                if value := element.get(attr):
                    return value.strip()
            elif element.text:
                return element.text.strip()
    return None


def _findall(
    parent: bs4.element.Tag,
    *names: str,
    attr: str | None = None,
    recursive=False,
):
    for element in parent.find_all(list(names), recursive=recursive):
        if attr:
            if value := element.get(attr):
                yield value.strip()
        elif element.text:
            yield element.text.strip()
