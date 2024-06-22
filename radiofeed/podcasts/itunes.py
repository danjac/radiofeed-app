import dataclasses
import functools
import itertools
import logging
from collections.abc import Iterator
from typing import Final

import httpx
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.functional import cached_property
from django.utils.http import urlsafe_base64_encode

from radiofeed.podcasts.models import Podcast

_CACHE_TIMEOUT: Final = 24 * 60 * 60

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

    def __init__(self, client: httpx.Client, search_term: str) -> None:
        self._client = client
        self._search_term = search_term

    def __len__(self) -> int:
        """Returns number of feeds."""
        return len(self.feeds)

    def __getitem__(self, key: int) -> Feed:
        """Return item by key"""
        return self.feeds[key]

    def __iter__(self) -> Iterator[Feed]:
        """Iterates feeds."""
        return self._insert_podcasts(self._parse_feeds(self._get_json()))

    @cached_property
    def feeds(self) -> list[Feed]:
        """Returns list of feeds."""
        return list(iter(self))

    def _get_json(self) -> dict:
        cache_key = search_cache_key(self._search_term)

        if cached := cache.get(cache_key):
            return cached

        try:
            data = self._get_response().json()
        except httpx.HTTPError as e:
            logging.error(e)
            return {}

        cache.set(cache_key, data, _CACHE_TIMEOUT)
        return data

    def _get_response(self):
        response = self._client.get(
            "https://itunes.apple.com/search",
            params={
                "term": self._search_term,
                "media": "podcast",
            },
            headers={
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        return response

    def _parse_feeds(self, json_data: dict) -> Iterator[Feed]:
        for result in json_data.get("results", []):
            try:
                yield Feed(
                    rss=result["feedUrl"],
                    url=result["collectionViewUrl"],
                    title=result["collectionName"],
                    image=result["artworkUrl600"],
                )
            except KeyError:
                continue

    def _insert_podcasts(self, feeds: Iterator[Feed]) -> Iterator[Feed]:
        feeds_for_podcasts, feeds = itertools.tee(feeds)

        podcasts = Podcast.objects.filter(
            rss__in={f.rss for f in feeds_for_podcasts}
        ).in_bulk(field_name="rss")

        # insert podcasts to feeds where we have a match

        feeds_for_insert, feeds = itertools.tee(
            (
                dataclasses.replace(feed, podcast=podcasts.get(feed.rss))
                for feed in feeds
            ),
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


def search(client: httpx.Client, search_term: str) -> FeedResultSet:
    """Runs cached search for podcasts on iTunes API."""
    return FeedResultSet(client, search_term)


@functools.cache
def search_cache_key(search_term: str) -> str:
    """Return cache key"""
    return "itunes:" + urlsafe_base64_encode(
        force_bytes(search_term.casefold(), "utf-8")
    )
