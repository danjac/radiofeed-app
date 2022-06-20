from __future__ import annotations

import base64
import dataclasses
import re

from typing import Generator
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
        feeds = search(search_term)
        cache.set(cache_key, feeds)
    return feeds


def search(search_term: str) -> list[Feed]:
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

    for url in parse_urls(
        get_response("https://itunes.apple.com/us/genre/podcasts/id26?mt=2").content,
        startswith="https://podcasts.apple.com/us/genre/podcasts",
    ):
        for batch in batcher(
            filter(
                None,
                map(
                    parse_podcast_id,
                    parse_urls(
                        get_response(url).content,
                        startswith="https://podcasts.apple.com/us/podcast/",
                    ),
                ),
            ),
            BATCH_SIZE,
        ):

            yield from parse_feeds(
                get_response(
                    "https://itunes.apple.com/lookup",
                    {
                        "id": ",".join(batch),
                        "entity": "podcast",
                    },
                ).json()
            )


def parse_feeds(data: dict) -> list[Feed]:
    """
    Adds any existing podcasts to result. Create any new podcasts if feed
    URL not found in database.
    """
    feeds: list[Feed] = []

    for result in data.get("results", []):
        try:
            feeds.append(
                Feed(
                    rss=result["feedUrl"],
                    url=result["collectionViewUrl"],
                    title=result["collectionName"],
                    image=result["artworkUrl600"],
                )
            )
        except KeyError:
            continue

    if not feeds:
        return []

    podcasts = Podcast.objects.filter(rss__in=[f.rss for f in feeds]).in_bulk(
        field_name="rss"
    )

    for_insert: list[Podcast] = []

    for feed in feeds:
        if podcast := podcasts.get(feed.rss):
            feed.podcast = podcast
        else:
            for_insert.append(Podcast(title=feed.title, rss=feed.rss))

    Podcast.objects.bulk_create(
        for_insert,
        ignore_conflicts=True,
        batch_size=BATCH_SIZE,
    )
    return feeds


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


def parse_urls(content: bytes, startswith: str) -> Generator[str, None, None]:
    for link in xml_parser.iterparse(content, "a"):
        if (href := link.attrib.get("href")) and href.startswith(startswith):
            yield href
