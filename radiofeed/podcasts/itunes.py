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

    # Attach existing podcasts to feeds
    podcasts = Podcast.objects.filter(
        rss__in={f.rss for f in feeds},
    ).in_bulk(field_name="rss")

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

        Podcast.objects.bulk_create(
            [Podcast(rss=feed.rss, promoted=True) for feed in feeds],
            unique_fields=["rss"],
            update_fields=["promoted"],
            update_conflicts=True,
        )

        # Unpromote any other promoted podcasts

        Podcast.objects.filter(promoted=True).exclude(
            rss__in={feed.rss for feed in feeds},
        ).update(promoted=False)

        return feeds
    return []


def _fetch_feeds(client: Client, url: str, **params) -> list[Feed]:
    """Fetches and parses feeds from iTunes API."""

    return list(
        {
            feed.rss: feed
            for feed in [
                _parse_feed(result)
                for result in _fetch_json(client, url, **params).get("results", [])
            ]
            if feed
        }.values()
    )


def _fetch_itunes_ids(client: Client, url: str, **params) -> set[str]:
    """Fetches podcast IDs from results."""
    return {
        itunes_id
        for itunes_id in [
            result.get("id")
            for result in _fetch_json(client, url, **params)
            .get("feed", {})
            .get("results", [])
        ]
        if itunes_id
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
