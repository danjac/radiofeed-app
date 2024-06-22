import dataclasses
import functools
import itertools
import logging
from collections.abc import Iterator

import httpx
from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.functional import cached_property
from django.utils.http import urlsafe_base64_encode

from radiofeed.podcasts.models import Podcast

logger = logging.getLogger(__name__)


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


class FeedResultSet:
    """Contains list of iTunes results.

    Example:

        qs = FeedResultSet(search_term)
        for feed in qs:
            ....
    """

    def __init__(self, feeds: Iterator[Feed]) -> None:
        self._feeds = feeds

    def __len__(self) -> int:
        """Returns number of feeds."""
        return len(self._result_cache)

    def __getitem__(self, key: int) -> Feed:
        """Return item by key"""
        return self._result_cache[key]

    def __iter__(self) -> Iterator[Feed]:
        """Iterates feeds."""
        return self._feeds

    @cached_property
    def _result_cache(self) -> list[Feed]:
        return list(iter(self))


def search(client: httpx.Client, search_term: str) -> FeedResultSet:
    """Runs cached search for podcasts on iTunes API."""
    return FeedResultSet(_search_feeds(client, search_term))


@functools.cache
def search_cache_key(search_term: str) -> str:
    """Return cache key"""
    return "itunes:" + urlsafe_base64_encode(
        force_bytes(search_term.casefold(), "utf-8")
    )


def _search_feeds(client: httpx.Client, search_term: str) -> Iterator[Feed]:
    return _insert_podcasts(_parse_feeds_from_json(_get_json(client, search_term)))


def _get_json(
    client: httpx.Client,
    search_term: str,
) -> dict:
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

    cache.set(cache_key, data, settings.CACHE_TIMEOUT)
    return data


def _parse_feeds_from_json(data: dict) -> Iterator[Feed]:
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


def _insert_podcasts(feeds: Iterator[Feed]) -> Iterator[Feed]:
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
