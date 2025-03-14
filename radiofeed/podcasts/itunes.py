import dataclasses
from collections.abc import Iterable

import httpx
from django.core.cache import cache
from django.db.models import Q

from radiofeed.http_client import Client
from radiofeed.podcasts.models import Podcast


class ItunesError(ValueError):
    """Base class for iTunes API errors."""


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

    def __hash__(self) -> int:
        """Hash based on RSS."""
        return hash(self.rss)


def search(client: Client, search_term: str, *, limit: int = 30) -> list[Feed]:
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

    podcasts = {
        podcast.rss: podcast.canonical or podcast
        for podcast in Podcast.objects.filter(
            rss__in={feed.rss for feed in feeds}
        ).select_related("canonical")
    }

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
    limit: int = 30,
    cache_timeout: int = 300,
) -> list[Feed]:
    """Search iTunes podcast API with caching."""
    search_term = search_term.strip().casefold()
    cache_key = f"search-itunes:{search_term}:{limit}"

    if (feeds := cache.get(cache_key)) is None:
        feeds = search(client, search_term, limit=limit)
        cache.set(cache_key, feeds, cache_timeout)

    return feeds


def fetch_chart(
    client: Client,
    *,
    country: str = "gb",
    limit: int = 30,
) -> list[Feed]:
    """Fetch top chart from iTunes podcast API. Any new podcasts will be added.
    All podcasts in the chart will be promoted.
    """

    feeds: list[Feed] = []

    if itunes_ids := _fetch_itunes_ids(
        client,
        f"https://rss.marketingtools.apple.com/api/v2/"
        f"{country}/podcasts/top-subscriber/{limit}/podcasts.json",
    ):
        feeds = _fetch_feeds(
            client,
            "https://itunes.apple.com/lookup",
            id=",".join(itunes_ids),
        )

        rss_feeds = {feed.rss for feed in feeds}

        q = Q(rss__in=rss_feeds) | Q(duplicates__rss__in=rss_feeds)

        # check duplicates
        rss_feeds |= set(Podcast.objects.filter(q).values_list("rss", flat=True))

        Podcast.objects.bulk_create(
            [Podcast(rss=rss, promoted=True) for rss in rss_feeds],
            unique_fields=["rss"],
            update_fields=["promoted"],
            update_conflicts=True,
        )

        Podcast.objects.filter(promoted=True).exclude(q).update(promoted=False)
    return feeds


def _fetch_feeds(client: Client, url: str, **params) -> list[Feed]:
    """Fetches and parses feeds from iTunes API."""
    return _orderedset(
        [
            feed
            for feed in [
                _parse_feed(result)
                for result in _fetch_json(client, url, **params).get("results", [])
            ]
            if feed
        ]
    )


def _fetch_itunes_ids(client: Client, url: str, **params) -> list[str]:
    """Fetches podcast IDs from results."""
    return _orderedset(
        [
            itunes_id
            for itunes_id in [
                result.get("id")
                for result in _fetch_json(client, url, **params)
                .get("feed", {})
                .get("results", [])
            ]
            if itunes_id
        ]
    )


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
    except httpx.HTTPError as e:
        raise ItunesError(f"Failed to fetch {url}: {e}") from e


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


def _orderedset(items: Iterable) -> list:
    return list(dict.fromkeys(items))
