import dataclasses
from collections.abc import Sequence

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
    """Search iTunes podcast API."""
    return _ItunesClient(client).search(search_term, limit=limit)


def search_cached(
    client: Client,
    search_term: str,
    *,
    limit: int = 50,
    cache_timeout: int = 3600,
) -> list[Feed]:
    """Search iTunes podcast API with caching."""
    search_term = search_term.strip().casefold()
    cache_key = f"search-itunes:{search_term}:{limit}"

    if (feeds := cache.get(cache_key)) is None:
        feeds = search(client, search_term, limit=limit)
        cache.set(cache_key, feeds, cache_timeout)

    return feeds


def fetch_chart(client: Client, *, location: str, limit: int = 50) -> list[Feed]:
    """Fetch top chart from iTunes podcast API."""
    return _ItunesClient(client).fetch_chart(location=location, limit=limit)


@dataclasses.dataclass(frozen=True)
class _ItunesClient:
    client: Client

    def search(self, search_term: str, *, limit: int = 50) -> list[Feed]:
        """Search iTunes podcast API."""
        feeds = self._fetch_search_feeds(search_term, limit)

        existing_podcasts = Podcast.objects.filter(
            rss__in={f.rss for f in feeds}
        ).in_bulk(field_name="rss")

        # Attach existing podcasts to feeds
        feeds = [
            dataclasses.replace(feed, podcast=existing_podcasts.get(feed.rss))
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

    def fetch_chart(self, *, location: str = "us", limit: int = 50) -> list[Feed]:
        """Fetch top chart from iTunes podcast API."""
        feeds = self._fetch_chart_feeds(location, limit)

        Podcast.objects.bulk_create(
            [Podcast(rss=feed.rss, promoted=True) for feed in feeds],
            unique_fields=["rss"],
            update_fields=["promoted"],
            update_conflicts=True,
        )

        return feeds

    def _fetch_search_feeds(self, search_term: str, limit: int) -> list[Feed]:
        return self._fetch_feeds(
            "https://itunes.apple.com/search",
            term=search_term,
            limit=limit,
            media="podcast",
        )

    def _fetch_chart_feeds(self, location: str, limit: int) -> list[Feed]:
        """Fetches feeds for the top chart podcasts."""
        itunes_ids = self._fetch_chart_ids(location, limit)
        return (
            self._fetch_feeds(
                "https://itunes.apple.com/lookup", id=",".join(itunes_ids)
            )
            if itunes_ids
            else []
        )

    def _fetch_chart_ids(self, location: str, limit: int) -> list[str]:
        """Fetches podcast IDs from the iTunes charts."""
        response = self._fetch_json(
            f"https://rss.marketingtools.apple.com/api/v2/{location}/podcasts/top/{limit}/podcasts.json"
        )
        return [
            result["id"]
            for result in response.get("feed", {}).get("results", [])
            if "id" in result
        ]

    def _fetch_json(self, url: str, **params) -> dict:
        """Fetches JSON response from the given URL."""
        try:
            response = self.client.get(
                url, params=params, headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return {}

    def _fetch_feeds(self, url: str, **params) -> list[Feed]:
        """Fetches and parses feeds from iTunes API."""
        return self._parse_feeds(self._fetch_json(url, **params).get("results", []))

    def _parse_feeds(self, source: Sequence[dict]) -> list[Feed]:
        """Parses unique feeds from API results."""
        seen_feeds = set()
        feeds = []

        for result in source:
            feed = self._parse_feed(result)
            if feed and feed.rss not in seen_feeds:
                seen_feeds.add(feed.rss)
                feeds.append(feed)

        return feeds

    def _parse_feed(self, feed: dict) -> Feed | None:
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
