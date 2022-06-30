import base64
import dataclasses
import itertools
import re

from urllib.parse import urlparse

import requests

from django.core.cache import cache

from radiofeed.common.parsers import xml_parser
from radiofeed.common.utils import batcher, get_user_agent
from radiofeed.podcasts.models import Podcast

BATCH_SIZE = 100

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


def crawl():
    """Crawl through iTunes podcast index and fetch RSS feeds for individual podcasts."""

    for location in LOCATIONS:
        for url in parse_genre_urls(location):
            for batch in batcher(parse_podcast_ids(url, location), BATCH_SIZE):
                yield from parse_feeds(
                    get_response(
                        "https://itunes.apple.com/lookup",
                        {
                            "id": ",".join(batch),
                            "entity": "podcast",
                        },
                    ).json(),
                )


def parse_feeds(json_data):
    """
    Adds any existing podcasts to result. Create any new podcasts if feed
    URL not found in database.
    """
    for batch in batcher(build_feeds_from_json(json_data), BATCH_SIZE):

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


def parse_genre_urls(location):
    return filter(
        lambda href: href.startswith(
            f"https://podcasts.apple.com/{location}/genre/podcasts"
        ),
        parse_urls(
            get_response(
                f"https://itunes.apple.com/{location}/genre/podcasts/id26"
            ).content
        ),
    )


def parse_podcast_ids(url, location):
    """Parse iTunes podcast IDs from provided URL"""
    return filter(
        None,
        map(
            parse_podcast_id,
            filter(
                lambda href: href.startswith(
                    f"https://podcasts.apple.com/{location}/podcast/"
                ),
                parse_urls(get_response(url).content),
            ),
        ),
    )


def parse_podcast_id(url):
    if match := RE_PODCAST_ID.search(urlparse(url).path.split("/")[-1]):
        return match.group("id")
    return None


def parse_urls(content):
    return filter(
        None,
        map(
            lambda el: el.attrib.get("href"),
            xml_parser.iterparse(content, "a"),
        ),
    )


def build_feeds_from_json(json_data):
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
