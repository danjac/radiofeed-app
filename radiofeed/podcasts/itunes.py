import dataclasses
import hashlib

import httpx
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from radiofeed.http_client import Client
from radiofeed.podcasts.models import Podcast


class ItunesError(Exception):
    """iTunes API error."""


@dataclasses.dataclass(frozen=True)
class Feed:
    """Encapsulates iTunes API result."""

    rss: str
    url: str
    title: str
    image: str

    def __str__(self) -> str:
        """Returns title of feed"""
        return self.title


def search(
    client: Client,
    search_term: str,
    *,
    limit: int = settings.DEFAULT_PAGE_SIZE,
) -> list[Feed]:
    """Search iTunes podcast API. New podcasts will be added to the database."""
    if feeds := _fetch_feeds(
        client,
        "https://itunes.apple.com/search",
        {
            "term": search_term,
            "limit": limit,
            "media": "podcast",
        },
    ):
        Podcast.objects.bulk_create(
            (
                Podcast(
                    rss=feed.rss,
                    title=feed.title,
                )
                for feed in feeds
            ),
            ignore_conflicts=True,
        )

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


def fetch_chart(client: Client, country: str, limit: int) -> list[Feed]:
    """Fetch top chart from iTunes podcast API. Any new podcasts will be added."""

    url = f"https://rss.marketingtools.apple.com/api/v2/{country}/podcasts/top/{limit}/podcasts.json"
    itunes_ids = _fetch_itunes_ids(client, url)

    if not itunes_ids:
        return []

    if feeds := _fetch_feeds(
        client,
        "https://itunes.apple.com/lookup",
        {
            "id": ",".join(itunes_ids),
        },
    ):
        with transaction.atomic():
            # demote current rankings
            Podcast.objects.filter(promoted=True).update(promoted=False)

            Podcast.objects.bulk_create(
                (Podcast(rss=url, promoted=True) for url in _get_canonical_urls(feeds)),
                unique_fields=["rss"],
                update_conflicts=True,
                update_fields=["promoted"],
            )

    return feeds


def _fetch_feeds(client: Client, url: str, params: dict) -> list[Feed]:
    """Fetches and parses feeds from iTunes API."""
    return [
        feed
        for feed in (
            _parse_feed(result)
            for result in _fetch_json(client, url, params).get("results", [])
        )
        if feed
    ]


def _fetch_itunes_ids(client: Client, url: str) -> set[str]:
    """Fetches podcast IDs from results."""
    return {
        itunes_id
        for itunes_id in (
            result.get("id")
            for result in _fetch_json(client, url).get("feed", {}).get("results", [])
        )
        if itunes_id
    }


def _fetch_json(client: Client, url: str, params: dict | None = None) -> dict:
    """Fetches JSON response from the given URL."""
    try:
        return client.get(
            url,
            params=params or {},
            headers={"Accept": "application/json"},
        ).json()
    except httpx.HTTPError as exc:
        raise ItunesError(str(exc)) from exc


def _parse_feed(feed: dict) -> Feed | None:
    """Parses a single feed entry."""
    try:
        return Feed(
            rss=feed["feedUrl"],
            url=feed["collectionViewUrl"],
            title=feed["collectionName"],
            image=feed["artworkUrl100"],
        )
    except KeyError:
        return None


def _get_canonical_urls(feeds: list[Feed]) -> list[str]:
    """Returns a list of canonical URLs for the given feeds."""

    # make sure we fetch only unique feeds in the right order
    urls = dict.fromkeys(feed.rss for feed in feeds).keys()

    # in certain cases, we may have duplicates in the database
    canonical_urls = dict(
        Podcast.objects.filter(
            duplicates__rss__in=urls,
        ).values_list("rss", "canonical")
    )

    return [canonical_urls.get(url, url) for url in urls]


def _get_cache_key(search_term: str, limit: int) -> str:
    value = search_term.strip().casefold()
    digest = hashlib.sha256(force_bytes(value)).digest()
    encoded = urlsafe_base64_encode(digest).rstrip("=")
    return f"itunes:{encoded}:{limit}"
