from __future__ import annotations

import base64
import io
import re

from typing import Generator
from urllib.parse import urlparse

import attr
import lxml
import requests

from django.core.cache import cache

from jcasts.podcasts import user_agent
from jcasts.podcasts.models import Podcast

LOOKUP_URL = "https://itunes.apple.com/lookup"
SEARCH_URL = "https://itunes.apple.com/search"

TOP_RATED_URL = (
    "https://rss.applemarketingtools.com/api/v2/us/podcasts/top/50/podcasts.json"
)

CRAWL_URL = "https://itunes.apple.com/us/genre/podcasts/id26?mt=2"

RE_PODCAST_ID = re.compile(r"id(?P<id>[0-9]+)")


@attr.s
class Feed:
    url: str = attr.ib()
    title: str = attr.ib(default="")
    image: str = attr.ib(default="")
    podcast: Podcast | None = attr.ib(default=None)


def search(search_term: str) -> Generator[Feed, None, None]:
    yield from parse_feeds(fetch_search(search_term))


def search_cached(search_term: str) -> list[Feed]:

    cache_key = "itunes:" + base64.urlsafe_b64encode(bytes(search_term, "utf-8")).hex()
    if (feeds := cache.get(cache_key)) is None:
        feeds = list(search(search_term))
        cache.set(cache_key, feeds)
    return feeds


def top_rated() -> Generator[Feed, None, None]:

    for result in fetch_top_rated()["feed"]["results"]:

        yield from parse_feeds(
            fetch_lookup(result["id"]),
            promoted=True,
        )


def crawl() -> Generator[Feed, None, None]:

    for url in parse_urls(get_response(CRAWL_URL).content):
        if url.startswith("https://podcasts.apple.com/us/genre/podcasts"):
            yield from parse_genre(url)


def parse_genre(genre_url: str) -> Generator[Feed, None, None]:

    for url in parse_urls(get_response(genre_url).content):
        if lookup_id := parse_podcast_id(url):
            try:
                yield from parse_feeds(fetch_lookup(lookup_id))
            except requests.RequestException:
                continue


def get_response(url, data: dict | None = None) -> requests.Response:
    response = requests.get(
        url,
        data,
        headers={"User-Agent": user_agent.get_user_agent()},
        timeout=10,
        allow_redirects=True,
    )
    response.raise_for_status()
    return response


def fetch_json(url: str, data: dict | None = None) -> dict:
    return get_response(url, data).json()


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


def parse_podcast_id(url: str) -> str | None:
    if url.startswith("https://podcasts.apple.com/us/podcast/") and (
        match := RE_PODCAST_ID.search(urlparse(url).path.split("/")[-1])
    ):
        return match.group("id")
    return None


def parse_urls(content: bytes) -> Generator[str, None, None]:
    for _, element in lxml.etree.iterparse(
        io.BytesIO(content),
        encoding="utf-8",
        no_network=True,
        resolve_entities=False,
        recover=True,
        events=("end",),
    ):
        if element.tag == "a" and (href := element.attrib.get("href")):
            yield href


def parse_feeds(data: dict, **defaults) -> Generator[Feed, None, None]:
    """
    Adds any existing podcasts to result. Create any new podcasts if feed
    URL not found in database.
    """

    if not (feeds := list(parse_results(data))):
        return

    podcasts = Podcast.objects.filter(rss__in=[f.url for f in feeds]).in_bulk(
        field_name="rss"
    )

    for_insert: list[Podcast] = []
    for_update: list[Podcast] = []

    for feed in feeds:

        feed.podcast = podcasts.get(feed.url, None)

        if feed.podcast is None:
            for_insert.append(Podcast(title=feed.title, rss=feed.url, **defaults))
        elif defaults:
            for k, v in defaults.items():
                setattr(feed.podcast, k, v)
            for_update.append(feed.podcast)

        yield feed

    if for_insert:
        Podcast.objects.bulk_create(for_insert, ignore_conflicts=True)

    if for_update and defaults:
        Podcast.objects.bulk_update(for_update, fields=defaults.keys())


def parse_results(data: dict) -> Generator[Feed, None, None]:

    for result in data.get("results", []):

        try:
            yield Feed(
                url=result["feedUrl"],
                title=result["collectionName"],
                image=result["artworkUrl600"],
            )
        except KeyError:
            pass
