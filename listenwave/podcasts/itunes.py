import contextlib
import functools
import hashlib
import json
import re
from collections.abc import Iterable, Iterator
from typing import Final

import httpx
from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from pydantic import BaseModel, Field, ValidationError

from listenwave.http_client import Client
from listenwave.podcasts.models import Podcast

COUNTRIES: Final = (
    "br",
    "cn",
    "cz",
    "de",
    "dk",
    "eg",
    "es",
    "fi",
    "fr",
    "gb",
    "hr",
    "hu",
    "it",
    "jp",
    "kr",
    "nl",
    "pl",
    "ro",
    "se",
    "tr",
    "ua",
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

    def __hash__(self) -> int:
        """Returns hash of feed based on RSS URL."""
        return hash(self.rss)


def search(client: Client, search_term: str, limit: int) -> list[Feed]:
    """Search iTunes podcast API."""
    return _fetch_feeds(
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
) -> tuple[list[Feed], bool]:
    """Search iTunes podcast API. Results are cached.
    Returns True if results were fetched from the API, False if from cache.
    """
    cache_key = _get_cache_key(search_term, limit)
    feeds = cache.get(cache_key, None)
    if feeds is None:
        feeds = search(client, search_term, limit=limit)
        cache.set(cache_key, feeds, timeout=cache_timeout)
        return feeds, True
    return feeds, False


def fetch_chart(client: Client, country: str, limit: int) -> list[Feed]:
    """Fetch top chart from iTunes podcast chart page. Any new podcasts will be added."""
    data = _fetch_json(
        client,
        f"https://rss.marketingtools.apple.com/api/v2/{country}/podcasts/top/{limit}/podcasts.json",
    )

    if feed_ids := set(_parse_chart_results(data)):
        return _fetch_feeds(
            client,
            "https://itunes.apple.com/lookup",
            {"id": ",".join(feed_ids)},
        )
    return []


def _fetch_feeds(client: Client, url: str, params: dict | None = None) -> list[Feed]:
    data = _fetch_json(client, url, params)
    return list(_parse_feeds(data.get("results", [])))


def save_feeds_to_db(feeds: Iterable[Feed], **fields) -> list[Podcast]:
    """Saves the given feeds to the database as Podcast objects."""
    podcasts = _build_podcasts_from_feeds(feeds, **fields)
    if fields:
        return Podcast.objects.bulk_create(
            podcasts,
            unique_fields=["rss"],
            update_conflicts=True,
            update_fields=fields,
        )
    return Podcast.objects.bulk_create(podcasts, ignore_conflicts=True)


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
        raise ItunesError(f"Failed to fetch JSON data from iTunes: {url}") from exc


def _parse_feeds(data: list[dict]) -> Iterator[Feed]:
    """Parses data into model objects."""
    for item in data:
        with contextlib.suppress(ValidationError):
            yield Feed(**item)


def _parse_chart_results(data: dict) -> Iterator[str]:
    for item in data.get("feed", {}).get("results", []):
        if (url := item.get("url")) and (match := re.search(r"/id(\d+)", url)):
            yield match.group(1)


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
