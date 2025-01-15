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
    return _insert_podcasts(
        _fetch_itunes_results(
            client,
            search_term,
            limit,
        ),
    )


def top_chart(client: Client) -> list[Podcast]:
    """Fetch top chart from iTunes podcast API."""
    with contextlib.suppress(httpx.HTTPError):
        response = client.get(_CHART_URL)
        if results := response.json().get("feed", {}).get("results", []):
            processes = []
            with futures.ThreadPoolExecutor() as executor:
                for result in results:
                    processes.append(
                        executor.submit(
                            _parse_top_chart_result,
                            client,
                            result,
                        )
                    )
            feed_urls = dict.fromkeys([process.result() for process in processes])
            podcasts = [
                Podcast(
                    rss=feed_url,
                    promoted=True,
                    itunes_ranking=ranking,
                )
                for ranking, feed_url in enumerate(feed_urls, 1)
                if feed_url
            ]
            return Podcast.objects.bulk_create(
                podcasts,
                unique_fields=["rss"],
                update_fields=["promoted", "itunes_ranking"],
                update_conflicts=True,
            )
    return []


def _parse_top_chart_result(client: Client, result: dict) -> str | None:
    with contextlib.suppress(KeyError, IndexError, httpx.HTTPError):
        response = client.get(
            "https://itunes.apple.com/lookup",
            params={"id": result["id"]},
        )
        return response.json()["results"][0]["feedUrl"]
    return None


def _fetch_itunes_results(
    client: Client, search_term: str, limit: int
) -> Iterator[Feed]:
    try:
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
            try:
                yield Feed(
                    rss=result["feedUrl"],
                    url=result["collectionViewUrl"],
                    title=result["collectionName"],
                    image=result["artworkUrl600"],
                )
            except KeyError:
                continue

    except httpx.HTTPError:
        return


def _insert_podcasts(
    feeds: Iterator[Feed],
    *,
    promoted: bool = False,
) -> Iterator[Feed]:
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
            Podcast(title=feed.title, rss=feed.rss, promoted=promoted)
            for feed in set(feeds_for_insert)
            if feed.podcast is None
        ],
        ignore_conflicts=True,
    )

    yield from feeds
