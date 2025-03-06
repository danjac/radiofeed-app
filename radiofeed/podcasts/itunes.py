import dataclasses

import httpx
from django.core.cache import cache

from radiofeed.http_client import Client
from radiofeed.podcasts.models import Podcast


@dataclasses.dataclass(frozen=True)
class Feed:
    """Encapsulates iTunes API result."""

    rss: str
    url: str
    title: str = ""
    image: str = ""
    podcast: Podcast | None = None

    def __str__(self) -> str:
        """Return title or RSS"""
        return self.title or self.rss


def search(client: Client, search_term: str, *, limit: int = 50) -> list[Feed]:
    """Search iTunes podcast API. New podcasts will be added.
    If the feed already exists, it will be attached to the Feed."""
    feeds = _fetch_feeds(
        client,
        "https://itunes.apple.com/search",
        term=search_term,
        limit=limit,
        media="podcast",
    )

    if not feeds:
        return []

    # Attach existing podcasts to feeds
    podcasts = Podcast.objects.filter(rss__in={f.rss for f in feeds}).in_bulk(
        field_name="rss"
    )

    feeds = [
        dataclasses.replace(
            feed,
            podcast=podcasts.get(feed.rss),
        )
        for feed in feeds
    ]

    # Create missing podcasts in bulk
    Podcast.objects.bulk_create(
        [
            Podcast(title=feed.title, rss=feed.rss)
            for feed in feeds
            if feed.podcast is None
        ],
        ignore_conflicts=True,
    )

    return feeds


def search_cached(
    client: Client,
    search_term: str,
    *,
    limit: int = 50,
    cache_timeout: int = 300,
) -> list[Feed]:
    """Search iTunes podcast API with caching."""
    search_term = search_term.strip().casefold()
    cache_key = f"search-itunes:{search_term}:{limit}"

    if (feeds := cache.get(cache_key)) is None:
        feeds = search(client, search_term, limit=limit)
        cache.set(cache_key, feeds, cache_timeout)

    return feeds


def fetch_chart(client: Client, *, location: str, limit: int = 50) -> list[Feed]:
    """Fetch top chart from iTunes podcast API. Any new podcasts will be added.
    All podcasts in the chart will be promoted.
    """
    if itunes_ids := _fetch_chart_ids(client, location, limit):
        feeds = _fetch_feeds(
            client,
            "https://itunes.apple.com/lookup",
            id=",".join(itunes_ids),
        )

        Podcast.objects.bulk_create(
            [Podcast(rss=feed.rss, promoted=True) for feed in feeds],
            unique_fields=["rss"],
            update_fields=["promoted"],
            update_conflicts=True,
        )

        return feeds
    return []


def _fetch_chart_ids(client: Client, location: str, limit: int) -> set[str]:
    """Fetches podcast IDs from the iTunes charts."""
    response = _fetch_json(
        client,
        f"https://rss.marketingtools.apple.com/api/v2/{location}/podcasts/top/{limit}/podcasts.json",
    )
    return {
        result["id"]
        for result in response.get("feed", {}).get("results", [])
        if "id" in result
    }


def _fetch_json(client: Client, url: str, **params) -> dict:
    """Fetches JSON response from the given URL."""
    try:
        response = client.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError:
        return {}


def _fetch_feeds(client: Client, url: str, **params) -> list[Feed]:
    """Fetches and parses feeds from iTunes API."""
    if results := _fetch_json(client, url, **params).get("results", []):
        feeds_dct: dict[str, Feed] = {}
        for result in results:
            if feed := _parse_feed(result):
                feeds_dct[feed.rss] = feed
        return list(feeds_dct.values())
    return []


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
