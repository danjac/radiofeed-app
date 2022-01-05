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

RE_PODCAST_ID = re.compile(r"id(?P<id>[0-9]+)")


@attr.s
class Feed:
    rss: str = attr.ib()
    url: str = attr.ib()
    title: str = attr.ib(default="")
    image: str = attr.ib(default="")
    podcast: Podcast | None = attr.ib(default=None)


def search_cached(search_term: str) -> list[Feed]:
    cache_key = "itunes:" + base64.urlsafe_b64encode(bytes(search_term, "utf-8")).hex()
    if (feeds := cache.get(cache_key)) is None:
        feeds = list(search(search_term))
        cache.set(cache_key, feeds)
    return feeds


def search(search_term: str) -> Generator[Feed, None, None]:
    """Search RSS feeds on iTunes"""
    yield from parse_feeds(
        get_response(
            "https://itunes.apple.com/search",
            {
                "term": search_term,
                "media": "podcast",
            },
        ).json()
    )


def top_rated() -> Generator[Feed, None, None]:
    """Get the top-rated iTunes feeds"""
    for result in get_response(
        "https://rss.applemarketingtools.com/api/v2/us/podcasts/top/50/podcasts.json"
    ).json()["feed"]["results"]:
        yield from parse_feeds(get_podcast(result["id"]), promoted=True)


def crawl() -> Generator[Feed, None, None]:
    """Crawl through iTunes podcast index and fetch RSS feeds for individual podcasts."""

    for url in parse_urls(
        get_response("https://itunes.apple.com/us/genre/podcasts/id26?mt=2").content
    ):
        if url.startswith("https://podcasts.apple.com/us/genre/podcasts"):
            yield from parse_genre(url)


def parse_genre(genre_url: str) -> Generator[Feed, None, None]:

    for url in parse_urls(get_response(genre_url).content):
        if podcast_id := parse_podcast_id(url):
            try:
                yield from parse_feeds(get_podcast(podcast_id))
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


def get_podcast(podcast_id: str) -> dict:
    return get_response(
        "https://itunes.apple.com/lookup",
        {
            "id": podcast_id,
            "entity": "podcast",
        },
    ).json()  # pragma: no cover


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

    podcasts = Podcast.objects.filter(rss__in=[f.rss for f in feeds]).in_bulk(
        field_name="rss"
    )

    for_insert: list[Podcast] = []
    for_update: list[Podcast] = []

    for feed in feeds:

        feed.podcast = podcasts.get(feed.rss, None)

        if feed.podcast is None:
            for_insert.append(Podcast(title=feed.title, rss=feed.rss, **defaults))
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
                rss=result["feedUrl"],
                url=result["collectionViewUrl"],
                title=result["collectionName"],
                image=result["artworkUrl600"],
            )
        except KeyError:
            pass
