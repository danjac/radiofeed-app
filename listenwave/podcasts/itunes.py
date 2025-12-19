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


def fetch_top_feeds(
    client: Client, country: str, genre_id: int | None = None
) -> list[Feed]:
    """Fetch top feeds from iTunes podcast chart page."""

    url = (
        f"https://podcasts.apple.com/{country}/genre/{genre_id}"
        if genre_id
        else f"https://podcasts.apple.com/{country}/charts"
    )

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

    feeds: list[Feed] = []

    # Batch requests to avoid URL length limits

    for batch in itertools.batched(itunes_ids, 200, strict=False):
        feeds += _fetch_feeds(
            client,
            "https://itunes.apple.com/lookup",
            {
                "id": ",".join(batch),
            },
        )

    return feeds


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


def _fetch_feeds(
    client: Client,
    url: str,
    params: dict | None = None,
) -> list[Feed]:
    try:
        response = client.get(
            url,
            params=params or {},
            headers={"Accept": "application/json"},
        )
        data = response.json()
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        raise ItunesError(f"{url}: {exc}") from exc

    feeds: list[Feed] = []
    for result in data.get("results", []):
        with contextlib.suppress(ValidationError):
            feeds.append(Feed(**result))
    return feeds


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
