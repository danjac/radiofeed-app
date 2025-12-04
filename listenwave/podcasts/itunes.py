import contextlib
import functools
import hashlib
import itertools
import json
import re
from collections.abc import Iterable, Iterator
from typing import Final

import httpx
import lxml.etree
from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from lxml import html
from pydantic import BaseModel, Field, ValidationError

from listenwave.http_client import Client
from listenwave.podcasts.models import Podcast

COUNTRIES: Final = (
    "br",
    "de",
    "dk",
    "es",
    "fi",
    "fr",
    "gb",
    "it",
    "ja",
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

    def __hash__(self) -> int:
        """Returns hash of feed based on RSS URL"""
        return hash(self.rss)


def search(
    client: Client,
    search_term: str,
    *,
    limit: int = settings.DEFAULT_PAGE_SIZE,
    **fields,
) -> list[Feed]:
    """Search iTunes podcast API. New podcasts will be added to the database."""
    feeds = list(
        _fetch_feeds_from_api(
            client,
            "https://itunes.apple.com/search",
            {
                "term": search_term,
                "limit": limit,
                "media": "podcast",
            },
        )
    )
    save_feeds_to_db(feeds, **fields)
    return feeds


def search_cached(
    client: Client,
    search_term: str,
    *,
    limit: int = settings.DEFAULT_PAGE_SIZE,
    cache_timeout: int = settings.DEFAULT_CACHE_TIMEOUT,
) -> list[Feed]:
    """Search iTunes podcast API. Results are cached."""
    cache_key = _get_cache_key(search_term, limit)
    feeds = cache.get(cache_key, None)
    if feeds is None:
        feeds = search(client, search_term, limit=limit)
        cache.set(cache_key, feeds, timeout=cache_timeout)
    return feeds


def fetch_chart(client: Client, country: str) -> Iterator[Feed]:
    """Fetch top chart from iTunes podcast chart page. Any new podcasts will be added."""
    return _fetch_feeds_from_page(
        client, f"https://podcasts.apple.com/{country}/charts"
    )


def fetch_genre(client: Client, country: str, genre_id: int) -> Iterator[Feed]:
    """Fetch top podcasts for the given genre from iTunes podcast chart page.
    Any new podcasts will be added.
    """
    return _fetch_feeds_from_page(
        client, f"https://podcasts.apple.com/{country}/genre/{genre_id}"
    )


def save_feeds_to_db(feeds: Iterable[Feed], **fields) -> list[Podcast]:
    """Saves the given feeds to the database."""
    podcasts = _build_podcasts_from_feeds(feeds, **fields)
    return (
        Podcast.objects.bulk_create(
            podcasts,
            unique_fields=["rss"],
            update_conflicts=True,
            update_fields=fields,
        )
        if fields
        else Podcast.objects.bulk_create(podcasts, ignore_conflicts=True)
    )


def _fetch_feeds_from_page(client: Client, url: str) -> Iterator[Feed]:
    try:
        response = client.get(url)
    except httpx.HTTPError as exc:
        raise ItunesError from exc

    try:
        tree = html.fromstring(response.content)
    except lxml.etree.ParserError as exc:
        raise ItunesError("Failed to parse iTunes chart page") from exc

    itunes_ids = set()

    for link in tree.xpath('//a[contains(@href, "/podcast/")]/@href'):
        if match := re.search(r"/id(\d+)", link):
            itunes_ids.add(match.group(1))

    for batch in itertools.batched(itunes_ids, 200, strict=False):
        yield from _fetch_feeds_from_api(
            client,
            "https://itunes.apple.com/lookup",
            {
                "id": ",".join(batch),
            },
        )


def _fetch_feeds_from_api(
    client: Client,
    url: str,
    params: dict | None = None,
) -> Iterator[Feed]:
    """Fetches and parses feeds from iTunes API."""

    try:
        response = client.get(
            url,
            params=params or {},
            headers={"Accept": "application/json"},
        )
    except httpx.HTTPError as exc:
        raise ItunesError(str(exc)) from exc

    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise ItunesError("Invalid response from iTunes") from exc

    for result in payload.get("results", []):
        with contextlib.suppress(ValidationError):
            yield Feed(**result)


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
