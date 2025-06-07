import dataclasses
from collections.abc import Iterator

import httpx
from django.conf import settings
from django.db import transaction

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
            [
                Podcast(
                    rss=feed.rss,
                    title=feed.title,
                )
                for feed in feeds
            ],
            ignore_conflicts=True,
        )

    return feeds


def search_lazy(client: Client, search_term: str, **kwargs) -> Iterator[Feed]:
    """Search iTunes podcast API. Results are evaluated lazily."""
    yield from search(client, search_term, **kwargs)


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
            Podcast.objects.filter(itunes_ranking__isnull=False).update(
                itunes_ranking=None
            )

            Podcast.objects.bulk_create(
                (
                    Podcast(rss=url, itunes_ranking=ranking)
                    for ranking, url in enumerate(_get_canonical_urls(feeds), start=1)
                ),
                unique_fields=["rss"],
                update_conflicts=True,
                update_fields=["itunes_ranking"],
            )

    return feeds


def _fetch_feeds(client: Client, url: str, params: dict) -> list[Feed]:
    """Fetches and parses feeds from iTunes API."""
    return [
        feed
        for feed in [
            _parse_feed(result)
            for result in _fetch_json(client, url, params).get("results", [])
        ]
        if feed
    ]


def _fetch_itunes_ids(client: Client, url: str) -> set[str]:
    """Fetches podcast IDs from results."""
    return {
        itunes_id
        for itunes_id in [
            result.get("id")
            for result in _fetch_json(client, url).get("feed", {}).get("results", [])
        ]
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
    urls = {feed.rss: feed for feed in feeds}.keys()

    # in certain cases, we may have duplicates in the database
    canonical_urls = dict(
        Podcast.objects.filter(
            duplicates__rss__in=urls,
        ).values_list("rss", "canonical")
    )

    return [canonical_urls.get(url, url) for url in urls]
