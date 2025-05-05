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


def search_lazy(
    client: Client,
    search_term: str,
    **kwargs,
) -> Iterator[Feed]:
    """Search iTunes podcast API. Results are evaluated lazily."""
    yield from search(client, search_term, **kwargs)


def fetch_chart(
    client: Client,
    country: str,
    *,
    limit: int = settings.DEFAULT_PAGE_SIZE,
) -> list[Feed]:
    """Fetch top chart from iTunes podcast API. Any new podcasts will be added.
    All podcasts in the chart will be promoted.
    """

    itunes_ids = _fetch_itunes_ids(
        client,
        f"https://rss.marketingtools.apple.com/api/v2/{country}/podcasts/top-subscriber/{limit}/podcasts.json",
    )

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
            # demote all promoted podcasts
            Podcast.objects.filter(promoted=True).update(promoted=False)

            rss_feeds = {feed.rss for feed in feeds}

            # check duplicates
            rss_feeds |= set(
                Podcast.objects.filter(duplicates__rss__in=rss_feeds).values_list(
                    "rss", flat=True
                )
            )

            # add or update podcasts
            Podcast.objects.bulk_create(
                [
                    Podcast(
                        rss=rss,
                        promoted=True,
                    )
                    for rss in rss_feeds
                ],
                unique_fields=["rss"],
                update_fields=["promoted"],
                update_conflicts=True,
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
