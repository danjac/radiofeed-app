from __future__ import annotations

import base64
import logging

import attr
import requests

from django.core.cache import cache
from jcasts.podcasts.feed_parser import parse_podcast_feed

from jcasts.podcasts.models import Podcast

SEARCH_URL = "https://itunes.apple.com/search"

logger = logging.getLogger(__name__)


@attr.s
class Feed:
    url: str = attr.ib()
    title: str = attr.ib(default="")
    image: str = attr.ib(default="")

    podcast: Podcast | None = None


def search(search_term: str) -> list[Feed]:
    try:
        return with_podcasts(
            parse_feed_data(
                fetch_json(
                    SEARCH_URL,
                    {
                        "term": search_term,
                        "media": "podcast",
                    },
                )
            )
        )
    except requests.RequestException as e:
        logger.exception(e)
        return []


def search_cached(search_term: str) -> list[Feed]:

    cache_key = "itunes:" + base64.urlsafe_b64encode(bytes(search_term, "utf-8")).hex()
    if (feeds := cache.get(cache_key)) is None:
        feeds = search(search_term)
        cache.set(cache_key, feeds)
    return feeds


def fetch_json(url: str, data: dict | None = None) -> dict:
    response = requests.get(url, data)
    response.raise_for_status()
    return response.json()


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


def with_podcasts(feeds: list[Feed]) -> list[Feed]:
    """Looks up podcast associated with result.

    If `add_new` is True, adds new podcasts if they are not already in the database"""

    podcasts = Podcast.objects.filter(rss__in=[f.url for f in feeds]).in_bulk(
        field_name="rss"
    )

    new_podcasts = []

    for feed in feeds:
        feed.podcast = podcasts.get(feed.url, None)
        if feed.podcast is None:
            new_podcasts.append(Podcast(title=feed.title, rss=feed.url))

    if new_podcasts:
        Podcast.objects.bulk_create(new_podcasts, ignore_conflicts=True)
        for podcast in new_podcasts:
            parse_podcast_feed.delay(podcast.id)

    return feeds
