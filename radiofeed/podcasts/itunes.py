import dataclasses
import itertools
from collections.abc import Iterator

import httpx
from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from radiofeed.podcasts.models import Podcast


class ItunesError(ValueError):
    """Custom Itunes exception."""


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


def search(client: httpx.Client, search_term: str) -> Iterator[Feed]:
    """Runs cached search for podcasts on iTunes API."""
    try:
        return _add_podcasts_to_feeds(_parse_feeds(_get_json(client, search_term)))
    except httpx.HTTPError as e:
        raise ItunesError from e


def search_cache_key(search_term: str) -> str:
    """Return cache key"""
    return "itunes:" + urlsafe_base64_encode(
        force_bytes(search_term.casefold(), "utf-8")
    )


def _parse_feeds(json_data: dict) -> Iterator[Feed]:
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


def _add_podcasts_to_feeds(feeds: Iterator[Feed]) -> Iterator[Feed]:
    feeds_for_podcasts, feeds = itertools.tee(feeds)

    podcasts = Podcast.objects.filter(
        rss__in={f.rss for f in feeds_for_podcasts}
    ).in_bulk(field_name="rss")

    feeds_for_insert, feeds = itertools.tee(
        (dataclasses.replace(feed, podcast=podcasts.get(feed.rss)) for feed in feeds),
    )

    Podcast.objects.bulk_create(
        (
            Podcast(title=feed.title, rss=feed.rss)
            for feed in set(feeds_for_insert)
            if feed.podcast is None
        ),
        ignore_conflicts=True,
    )

    yield from feeds


def _get_json(client: httpx.Client, search_term: str) -> dict:
    cache_key = search_cache_key(search_term)

    if cached := cache.get(cache_key):
        return cached

    data = _get_response(client, search_term).json()
    cache.set(cache_key, data, settings.CACHE_TIMEOUT)
    return data


def _get_response(client: httpx.Client, search_term: str):
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
    return response
