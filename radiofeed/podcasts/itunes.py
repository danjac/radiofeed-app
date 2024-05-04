import dataclasses
import itertools
from collections.abc import Iterator

import httpx

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


def search(client: httpx.Client, search_term: str) -> Iterator[Feed]:
    """Runs cached search for podcasts on iTunes API."""
    response = _get_response(
        client,
        "https://itunes.apple.com/search",
        params={
            "term": search_term,
            "media": "podcast",
        },
        headers={
            "Accept": "application/json",
        },
    )
    yield from _parse_feeds(response)


def _parse_feeds(
    response: httpx.Response,
) -> Iterator[Feed]:
    for batch in itertools.batched(
        _build_feeds_from_json(response.json()),
        100,
    ):
        Podcast.objects.bulk_create(
            (Podcast(title=feed.title, rss=feed.rss) for feed in set(batch)),
            ignore_conflicts=True,
        )

        yield from batch


def _build_feeds_from_json(json_data: dict) -> Iterator[Feed]:
    for result in json_data.get("results", []):
        try:
            yield Feed(
                rss=result["feedUrl"],
                url=result["collectionViewUrl"],
                title=result["collectionName"],
                image=result["artworkUrl600"],
            )
        except KeyError:
            continue


def _get_response(
    client: httpx.Client,
    url,
    params: dict | None = None,
    headers: dict | None = None,
    **kwargs,
):
    response = client.get(
        url,
        params=params,
        headers=headers,
        **kwargs,
    )
    response.raise_for_status()
    return response
