import dataclasses
import functools
import itertools
import logging
from collections.abc import Iterator
from typing import Final, TypeAlias

import httpx
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.functional import cached_property
from django.utils.http import urlsafe_base64_encode

from radiofeed.podcasts.models import Podcast

logger = logging.getLogger(__name__)

_CACHE_TIMEOUT: Final = 60 * 60 * 24


@dataclasses.dataclass(frozen=True)
class Feed:
    """Encapsulates iTunes API result.

    Attributes:
        rss: URL to RSS or Atom resource
        url: URL to website of podcast
        title: title of podcast
        image: URL to cover image
        podcast: matching Podcast instance in local database
    """

    rss: str
    url: str
    title: str = ""
    image: str = ""
    podcast: Podcast | None = None


FeedIterator: TypeAlias = Iterator[Feed]


class FeedResultSet:
    """Pagination-friendly way to handle iterator."""

    def __init__(self, feeds: FeedIterator, length: int) -> None:
        self._feeds = feeds
        self._length = length

    def __len__(self) -> int:
        """Returns number of feeds."""
        return self._length

    def __getitem__(self, index: int) -> Feed:
        """Return item by index"""
        return self._result_cache[index]

    @cached_property
    def _result_cache(self) -> list[Feed]:
        return list(self._feeds)


def search(client: httpx.Client, search_term: str) -> FeedResultSet:
    """Runs cached search for podcasts on iTunes API."""
    response = _get_response(client, search_term)

    try:
        length = int(response["resultCount"])
    except (KeyError, ValueError):
        length = 0

    return FeedResultSet(
        _insert_podcasts(_parse_feeds_from_json(response)),
        length=length,
    )


@functools.cache
def search_cache_key(search_term: str) -> str:
    """Return cache key"""
    return "itunes:" + urlsafe_base64_encode(
        force_bytes(search_term.casefold(), "utf-8")
    )


def _get_response(client: httpx.Client, search_term: str) -> dict:
    cache_key = search_cache_key(search_term)

    if cached := cache.get(cache_key):
        return cached

    try:
        response = client.get(
            "https://itunes.apple.com/search",
            params={
                "term": search_term,
                "media": "podcast",
            },
            headers={
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()

    except httpx.HTTPError as e:
        logging.error(e)
        return {}

    cache.set(cache_key, data, _CACHE_TIMEOUT)
    return data


def _parse_feeds_from_json(data: dict) -> FeedIterator:
    for result in data.get("results", []):
        try:
            yield Feed(
                rss=result["feedUrl"],
                url=result["collectionViewUrl"],
                title=result["collectionName"],
                image=result["artworkUrl600"],
            )
        except KeyError:
            continue


def _insert_podcasts(feeds: FeedIterator) -> FeedIterator:
    feeds_for_podcasts, feeds = itertools.tee(feeds)

    podcasts = Podcast.objects.filter(
        rss__in={f.rss for f in feeds_for_podcasts}
    ).in_bulk(field_name="rss")

    # insert podcasts to feeds where we have a match

    feeds_for_insert, feeds = itertools.tee(
        (dataclasses.replace(feed, podcast=podcasts.get(feed.rss)) for feed in feeds),
    )

    # create new podcasts for feeds without a match

    Podcast.objects.bulk_create(
        (
            Podcast(title=feed.title, rss=feed.rss)
            for feed in set(feeds_for_insert)
            if feed.podcast is None
        ),
        ignore_conflicts=True,
    )

    yield from feeds
