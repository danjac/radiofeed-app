import base64
import dataclasses
import itertools
import re

from urllib.parse import urlparse

import requests

from django.core.cache import cache

from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.parsers import xml_parser
from radiofeed.podcasts.utils import batcher, get_user_agent

RE_PODCAST_ID = re.compile(r"id(?P<id>\d+)")

LOCATIONS = (
    "de",
    "fi",
    "fr",
    "gb",
    "se",
    "us",
)


@dataclasses.dataclass
class Feed:
    rss: str
    url: str
    title: str = ""
    image: str = ""
    podcast: Podcast | None = None


def search_cached(search_term):
    cache_key = "itunes:" + base64.urlsafe_b64encode(bytes(search_term, "utf-8")).hex()
    if (feeds := cache.get(cache_key)) is None:
        feeds = list(search(search_term))
        cache.set(cache_key, feeds)
    return feeds


def search(search_term):
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


def crawl(batch_size=100):
    """Crawl through iTunes podcast index and fetch RSS feeds for individual podcasts."""

    for location in LOCATIONS:
        for url in get_genre_urls(location):
            for batch in batcher(parse_podcast_ids(url, location), batch_size):
                yield from parse_feeds(
                    get_response(
                        "https://itunes.apple.com/lookup",
                        {
                            "id": ",".join(batch),
                            "entity": "podcast",
                        },
                    ).json(),
                    batch_size,
                )


def parse_feeds(data, batch_size=100):
    """
    Adds any existing podcasts to result. Create any new podcasts if feed
    URL not found in database.
    """
    for batch in batcher(parse_results(data), batch_size):

        feeds_for_podcasts, feeds = itertools.tee(batch)

        podcasts = Podcast.objects.filter(
            rss__in=set([f.rss for f in feeds_for_podcasts])
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
            ignore_conflicts=True,
        )

        yield from feeds


def get_response(url, data=None):
    response = requests.get(
        url,
        data,
        headers={"User-Agent": get_user_agent()},
        timeout=10,
        allow_redirects=True,
    )
    response.raise_for_status()
    return response


def parse_results(data):
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


def get_genre_urls(location):
    return parse_urls(
        f"https://itunes.apple.com/{location}/genre/podcasts/id26",
        f"https://podcasts.apple.com/{location}/genre/podcasts",
    )


def parse_podcast_ids(url, location):
    """Parse iTunes podcast IDs from provided URL"""
    return filter(
        None,
        map(
            parse_podcast_id,
            parse_urls(
                url,
                f"https://podcasts.apple.com/{location}/podcast/",
            ),
        ),
    )


def parse_urls(url, startswith):
    """Fetches all urls from a page starting with a given string"""
    return filter(
        lambda href: href and href.startswith(startswith),
        map(
            lambda el: el.attrib.get("href"),
            xml_parser.iterparse(get_response(url).content, "a"),
        ),
    )


def parse_podcast_id(url):
    if match := RE_PODCAST_ID.search(urlparse(url).path.split("/")[-1]):
        return match.group("id")
    return None
