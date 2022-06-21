from __future__ import annotations

import base64
import dataclasses
import itertools
import re

from typing import Generator, Iterable
from urllib.parse import urlparse

import requests

from django.core.cache import cache

from radiofeed.podcasts.feed_updater import batcher, get_user_agent
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.parsers import xml_parser

RE_PODCAST_ID = re.compile(r"id(?P<id>\d+)")
BATCH_SIZE = 100


@dataclasses.dataclass
class Feed:
    rss: str
    url: str
    title: str = ""
    image: str = ""
    podcast: Podcast | None = None


def search_cached(search_term: str) -> list[Feed]:
    cache_key = "itunes:" + base64.urlsafe_b64encode(bytes(search_term, "utf-8")).hex()
    if (feeds := cache.get(cache_key)) is None:
        feeds = list(search(search_term))
        cache.set(cache_key, feeds)
    return feeds


def search(search_term: str) -> Iterable[Feed]:
    """Search RSS feeds on iTunes"""
    return parse_feeds(
        get_response(
            "https://itunes.apple.com/search",
            {
                "term": search_term,
                "media": "podcast",
            },
        ).json()
    )


def crawl() -> Generator[Feed, None, None]:
    """Crawl through iTunes podcast index and fetch RSS feeds for individual podcasts."""

    for url in get_genre_urls():
        for batch in batcher(get_podcast_ids(url), BATCH_SIZE):
            yield from parse_feeds(
                get_response(
                    "https://itunes.apple.com/lookup",
                    {
                        "id": ",".join(batch),
                        "entity": "podcast",
                    },
                ).json()
            )


def parse_feeds(data: dict) -> Generator[Feed, None, None]:
    """
    Adds any existing podcasts to result. Create any new podcasts if feed
    URL not found in database.
    """
    for batch in batcher(parse_results(data), BATCH_SIZE):

        feeds_for_podcasts, feeds = itertools.tee(batch)

        podcasts = Podcast.objects.filter(
            rss__in=[f.rss for f in feeds_for_podcasts]
        ).in_bulk(field_name="rss")

        feeds_for_insert, feeds = itertools.tee(
            map(
                lambda feed: dataclasses.replace(feed, podcast=podcasts.get(feed.rss)),
                feeds,
            ),
        )

        Podcast.objects.bulk_create(
            map(
                lambda feed: Podcast(title=feed.title, rss=feed.rss),
                filter(lambda feed: feed.podcast is None, feeds_for_insert),
            ),
            batch_size=BATCH_SIZE,
        )

        yield from feeds


def get_response(url, data: dict | None = None) -> requests.Response:
    response = requests.get(
        url,
        data,
        headers={"User-Agent": get_user_agent()},
        timeout=10,
        allow_redirects=True,
    )
    response.raise_for_status()
    return response


def parse_podcast_id(url: str) -> str | None:
    if match := RE_PODCAST_ID.search(urlparse(url).path.split("/")[-1]):
        return match.group("id")
    return None


def parse_results(data: dict) -> Generator[Feed, None, None]:
    for result in data.get("results", []):
        try:
            yield Feed(
                rss=result["feedUrl"],
                url=result["collectionViewUrl"],
                title=result["collectionName"],
                image=result["artworkUrl600"],
            )
        except KeyError:
            continue


def get_genre_urls() -> filter[str]:
    return filter(
        lambda url: url.startswith("https://podcasts.apple.com/us/genre/podcasts"),
        parse_urls(
            get_response(
                "https://itunes.apple.com/us/genre/podcasts/id26?mt=2"
            ).content,
        ),
    )


def get_podcast_ids(url: str) -> filter[str]:
    return filter(
        None,
        map(
            parse_podcast_id,
            filter(
                lambda url: url.startswith("https://podcasts.apple.com/us/podcast/"),
                parse_urls(get_response(url).content),
            ),
        ),
    )


def parse_urls(content: bytes) -> filter[str]:
    return filter(
        None,
        map(
            lambda el: el.attrib.get("href"),
            xml_parser.iterparse(content, "a"),
        ),
    )
