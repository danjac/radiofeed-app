from __future__ import annotations

import base64
import logging

import attr
import requests

from django.core.cache import cache

from jcasts.podcasts.models import Podcast

LOOKUP_URL = "https://itunes.apple.com/lookup"
SEARCH_URL = "https://itunes.apple.com/search"

TOP_RATED_URL = (
    "https://rss.applemarketingtools.com/api/v2/us/podcasts/top/50/podcasts.json"
)

logger = logging.getLogger(__name__)


@attr.s
class Feed:
    url: str = attr.ib()
    title: str = attr.ib(default="")
    image: str = attr.ib(default="")

    podcast: Podcast | None = None


def search(search_term: str) -> list[Feed]:
    try:
        return with_podcasts(parse_feed_data(fetch_search(search_term)))
    except requests.RequestException as e:
        logger.exception(e)
        return []


def search_cached(search_term: str) -> list[Feed]:

    cache_key = "itunes:" + base64.urlsafe_b64encode(bytes(search_term, "utf-8")).hex()
    if (feeds := cache.get(cache_key)) is None:
        feeds = search(search_term)
        cache.set(cache_key, feeds)
    return feeds


def top_rated() -> list[Feed]:
    try:
        feeds = []

        for result in fetch_top_rated()["feed"]["results"]:
            feeds += with_podcasts(
                parse_feed_data(fetch_lookup(result["id"])),
                promoted=True,
            )

        Podcast.objects.filter(
            pk__in=[feed.podcast.id for feed in feeds if feed.podcast]
        ).update(promoted=True)

        return feeds
    except requests.RequestException as e:
        logger.exception(e)
        return []


def fetch_json(url: str, data: dict | None = None) -> dict:
    response = requests.get(url, data)
    response.raise_for_status()
    return response.json()


def fetch_search(term: str) -> dict:
    return fetch_json(
        SEARCH_URL,
        {
            "term": term,
            "media": "podcast",
        },
    )


def fetch_top_rated() -> dict:
    return fetch_json(TOP_RATED_URL)  # pragma: no cover


def fetch_lookup(lookup_id: str) -> dict:
    return fetch_json(
        LOOKUP_URL, {"id": lookup_id, "entity": "podcast"}
    )  # pragma: no cover


def parse_feed_data(data: dict) -> list[Feed]:
    def _parse_feed(result: dict) -> Feed | None:
        try:
            return Feed(
                url=result["feedUrl"],
                title=result["collectionName"],
                image=result["artworkUrl600"],
            )
        except KeyError:
            return None

    return [
        feed
        for feed in [_parse_feed(result) for result in data.get("results", [])]
        if feed
    ]


def with_podcasts(feeds: list[Feed], **defaults) -> list[Feed]:
    """Looks up podcast associated with result.

    If `add_new` is True, adds new podcasts if they are not already in the database"""
    print("feeds", feeds)

    podcasts = Podcast.objects.filter(rss__in=[f.url for f in feeds]).in_bulk(
        field_name="rss"
    )

    new_podcasts = []

    for feed in feeds:
        feed.podcast = podcasts.get(feed.url, None)
        if feed.podcast is None:
            new_podcasts.append(Podcast(title=feed.title, rss=feed.url, **defaults))

    if new_podcasts:
        Podcast.objects.bulk_create(new_podcasts, ignore_conflicts=True)

    return feeds
