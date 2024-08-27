import dataclasses
import itertools
from collections.abc import Iterator

import httpx
from django.conf import settings

from radiofeed.http_client import Client
from radiofeed.podcasts.models import Podcast


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


def search(
    client: Client,
    search_term: str,
    limit: int = settings.PAGE_SIZE,
) -> Iterator[Feed]:
    """Runs cached search for podcasts on iTunes API."""
    return _insert_podcasts(_parse_feeds_from_json(client, search_term, limit))


def _get_response(client: Client, search_term: str, limit: int) -> dict:
    try:
        response = client.get(
            "https://itunes.apple.com/search",
            params={
                "term": search_term,
                "media": "podcast",
            },
            headers={
                "Accept": "application/json",
            },
        )
        return response.json()

    except httpx.HTTPError:
        return {}


def _parse_feeds_from_json(
    client: Client, search_term: str, limit: int
) -> Iterator[Feed]:
    for result in _get_response(client, search_term, limit).get("results", []):
        try:
            yield Feed(
                rss=result["feedUrl"],
                url=result["collectionViewUrl"],
                title=result["collectionName"],
                image=result["artworkUrl600"],
            )
        except KeyError:
            continue


def _insert_podcasts(feeds: Iterator[Feed]) -> Iterator[Feed]:
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
