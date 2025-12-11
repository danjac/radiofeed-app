import contextlib
import functools
import hashlib
import itertools
import json
import re
from collections.abc import Iterable, Iterator
from typing import Final, TypeVar

import httpx
from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from pydantic import BaseModel, Field, ValidationError

from listenwave.http_client import Client
from listenwave.podcasts.models import Podcast

T_Model = TypeVar("T_Model", bound=BaseModel)

COUNTRIES: Final = (
    "br",
    "de",
    "dk",
    "es",
    "fi",
    "fr",
    "gb",
    "it",
    "kr",
    "pl",
    "se",
    "us",
)


class ItunesError(Exception):
    """iTunes API error."""


class Feed(BaseModel):
    """Encapsulates iTunes API result."""

    rss: str = Field(..., alias="feedUrl")
    url: str = Field(..., alias="collectionViewUrl")
    title: str = Field(..., alias="collectionName")
    image: str = Field(..., alias="artworkUrl100")

    def __str__(self) -> str:
        """Returns title of feed"""
        return self.title


class ChartItem(BaseModel):
    """Encapsulates iTunes chart item."""

    url: str


def search(client: Client, search_term: str, limit: int) -> Iterator[Feed]:
    """Search iTunes podcast API. New podcasts will be added to the database."""
    yield from _fetch_and_save_feeds(
        client,
        "https://itunes.apple.com/search",
        {
            "term": search_term,
            "limit": limit,
            "media": "podcast",
        },
    )


def search_cached(
    client: Client,
    search_term: str,
    limit: int,
    cache_timeout: int = settings.DEFAULT_CACHE_TIMEOUT,
) -> list[Feed]:
    """Search iTunes podcast API. Results are cached."""
    cache_key = _get_cache_key(search_term, limit)
    feeds = cache.get(cache_key, None)
    if feeds is None:
        feeds = list(search(client, search_term, limit=limit))
        cache.set(cache_key, feeds, timeout=cache_timeout)
    return feeds


def fetch_chart(
    client: Client,
    country: str,
    limit: int,
    **fields,
) -> Iterator[Feed]:
    """Fetch top chart from iTunes podcast chart page. Any new podcasts will be added."""
    data = _fetch_json(
        client,
        f"https://rss.marketingtools.apple.com/api/v2/{country}/podcasts/top/{limit}/podcasts.json",
    )

    if feed_ids := {
        feed_id
        for feed_id in (
            _parse_feed_id_from_url(item.url)
            for item in _parse_json(
                ChartItem,
                data.get("feed", {}).get("results", []),
            )
        )
        if feed_id
    }:
        yield from _fetch_and_save_feeds(
            client,
            "https://itunes.apple.com/lookup",
            {"id": ",".join(feed_ids)},
            **fields,
        )


def _fetch_and_save_feeds(
    client: Client,
    url: str,
    params: dict | None = None,
    **fields,
) -> Iterator[Feed]:
    data = _fetch_json(client, url, params)
    feeds, feeds_to_save = itertools.tee(_parse_json(Feed, data.get("results", [])))
    podcasts = _build_podcasts_from_feeds(feeds_to_save, **fields)
    if fields:
        Podcast.objects.bulk_create(
            podcasts,
            unique_fields=["rss"],
            update_conflicts=True,
            update_fields=fields,
        )
    else:
        Podcast.objects.bulk_create(podcasts, ignore_conflicts=True)

    return feeds


def _fetch_json(client: Client, url: str, params: dict | None = None) -> dict:
    """Fetches JSON data from the given URL."""
    try:
        response = client.get(
            url,
            params=params or {},
            headers={"Accept": "application/json"},
        )
        return response.json()
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        raise ItunesError("Failed to fetch JSON data from iTunes") from exc


def _parse_json(model: type[T_Model], data: list[dict]) -> Iterator[T_Model]:
    """Parses data into model objects."""
    for item in data:
        with contextlib.suppress(ValidationError):
            yield model(**item)


def _parse_feed_id_from_url(url: str) -> str | None:
    if match := re.search(r"/id(\d+)", url):
        return match.group(1)
    return None


def _build_podcasts_from_feeds(feeds: Iterable[Feed], **fields) -> Iterator[Podcast]:
    """Returns a list of podcasts with canonical URLs for the given feeds."""

    # make sure we fetch only unique feeds in the right order
    urls = dict.fromkeys(feed.rss for feed in feeds).keys()

    # in certain cases, we may have duplicates in the database
    # find the canonical URLs for the given URLs
    canonical_urls = dict(
        Podcast.objects.filter(
            rss__in=urls,
            canonical__isnull=False,
        ).values_list("rss", "canonical__rss")
    )

    for url in urls:
        yield Podcast(rss=canonical_urls.get(url, url), **fields)


@functools.cache
def _get_cache_key(search_term: str, limit: int) -> str:
    value = search_term.strip().casefold()
    digest = hashlib.sha256(force_bytes(value)).digest()
    encoded = urlsafe_base64_encode(digest).rstrip("=")
    return f"itunes:{encoded}:{limit}"
