import contextlib
import dataclasses
import itertools
from collections.abc import Iterator
from concurrent import futures
from typing import Final

import httpx

from radiofeed.http_client import Client
from radiofeed.podcasts.models import Podcast

_CHART_URL: Final = (
    "https://rss.marketingtools.apple.com/api/v2/us/podcasts/top/10/podcasts.json"
)


@dataclasses.dataclass(frozen=True)
class Feed:
    """Encapsulates iTunes API result.

    Attributes:
        rss: URL to RSS or Atom resource
        url: URL to website of podcast
        title: title of podcast
        image: URL to cover image
        podcast: matching Podcast instance in local database
    """

    rss: str
    url: str
    title: str = ""
    image: str = ""
    podcast: Podcast | None = None


def search(client: Client, search_term: str, *, limit: int = 50) -> Iterator[Feed]:
    """Search iTunes podcast API."""
    return _insert_search_results(
        _fetch_search_results(
            client,
            search_term,
            limit,
        ),
    )


def fetch_top_chart(client: Client) -> list[Podcast]:
    """Fetch top chart from iTunes podcast API.
    New or updated podcasts are inserted or updated with `promoted=True`.
    """
    return Podcast.objects.bulk_create(
        [
            Podcast(
                rss=feed_url,
                promoted=True,
            )
            for feed_url in _parse_top_chart_feed_urls(client)
        ],
        unique_fields=["rss"],
        update_fields=["promoted"],
        update_conflicts=True,
    )


def _fetch_search_results(
    client: Client,
    search_term: str,
    limit: int,
) -> Iterator[Feed]:
    with contextlib.suppress(httpx.HTTPError):
        response = client.get(
            "https://itunes.apple.com/search",
            params={
                "term": search_term,
                "limit": limit,
                "media": "podcast",
            },
            headers={
                "Accept": "application/json",
            },
        )
        for result in response.json().get("results", []):
            with contextlib.suppress(KeyError):
                yield Feed(
                    rss=result["feedUrl"],
                    url=result["collectionViewUrl"],
                    title=result["collectionName"],
                    image=result["artworkUrl100"],
                )


def _insert_search_results(feeds: Iterator[Feed]) -> Iterator[Feed]:
    # find or insert podcasts from local database into feeds
    feeds_for_podcasts, feeds = itertools.tee(feeds)

    podcasts = Podcast.objects.filter(
        rss__in={f.rss for f in feeds_for_podcasts}
    ).in_bulk(field_name="rss")

    # insert podcasts to feeds where we have a match

    feeds_for_insert, feeds = itertools.tee(
        [dataclasses.replace(feed, podcast=podcasts.get(feed.rss)) for feed in feeds],
    )

    # create new podcasts for feeds without a match

    Podcast.objects.bulk_create(
        [
            Podcast(title=feed.title, rss=feed.rss)
            for feed in set(feeds_for_insert)
            if feed.podcast is None
        ],
        ignore_conflicts=True,
    )

    yield from feeds


def _parse_top_chart_feed_urls(client: Client) -> set[str]:
    with contextlib.suppress(httpx.HTTPError):
        response = client.get(_CHART_URL)
        itunes_ids = {
            itunes_id
            for itunes_id in [
                result.get("id", None)
                for result in response.json().get("feed", {}).get("results", [])
            ]
            if itunes_id
        }
        with futures.ThreadPoolExecutor() as executor:
            return {
                feed_url
                for feed_url in executor.map(
                    lambda itunes_id: _parse_top_chart_result(client, itunes_id),
                    itunes_ids,
                )
                if feed_url
            }
    return set()


def _parse_top_chart_result(client: Client, itunes_id: str) -> str | None:
    with contextlib.suppress(KeyError, IndexError, httpx.HTTPError):
        response = client.get(
            "https://itunes.apple.com/lookup",
            params={
                "id": itunes_id,
            },
            headers={
                "Accept": "application/json",
            },
        )
        return response.json()["results"][0]["feedUrl"]
    return None
