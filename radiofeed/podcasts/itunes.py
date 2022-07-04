import base64
import dataclasses
import itertools
import re

from urllib.parse import urlparse

import requests

from django.conf import settings
from django.core.cache import cache

from radiofeed.common.utils.iterators import batcher
from radiofeed.common.utils.xml import parse_xml
from radiofeed.podcasts.models import Podcast

_batch_size = 100

_itunes_podcast_id_re = re.compile(r"id(?P<id>\d+)")


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


def search_cached(search_term):
    """Runs cached search for podcasts on iTunes API.

    Args:
        search_term (str): search term(s)

    Returns:
        list[Feed]
    """
    cache_key = "itunes:" + base64.urlsafe_b64encode(bytes(search_term, "utf-8")).hex()
    if (feeds := cache.get(cache_key)) is None:
        feeds = list(search(search_term))
        cache.set(cache_key, feeds)
    return feeds


def search(search_term):
    """Runs search for podcasts on iTunes API.

    Args:
        search_term (str): search term(s)

    Returns:
        list[Feed]
    """
    return _parse_feeds(
        _get_response(
            "https://itunes.apple.com/search",
            {
                "term": search_term,
                "media": "podcast",
            },
        ).json()
    )


def crawl(locations):
    """Crawls iTunes podcast catalog and creates new Podcast instances from any new feeds found.

    Args:
        locations (list[str]): list of iTunes country locations e.g. "us", "gb"

    Yields:
        Feed: any new or existing feeds
    """
    for location in settings.ITUNES_LOCATIONS:
        yield from Crawler(location).crawl()


class Crawler:
    """Crawls iTunes podcast catalog.

    Args:
        location (str): country location e.g. "us"
    """

    def __init__(self, location):
        self._location = location

    def crawl(self):
        """Crawls through location and finds new feeds, adding any new podcasts to the database.

        Yields:
            Feed
        """
        for url in self._parse_genre_urls():
            for batch in batcher(self._parse_podcast_ids(url), _batch_size):
                yield from _parse_feeds(
                    _get_response(
                        "https://itunes.apple.com/lookup",
                        {
                            "id": ",".join(batch),
                            "entity": "podcast",
                        },
                    ).json(),
                )

    def _parse_genre_urls(self):
        return (
            href
            for href in self._parse_urls(
                _get_response(
                    f"https://itunes.apple.com/{self._location}/genre/podcasts/id26"
                ).content
            )
            if href.startswith(
                f"https://podcasts.apple.com/{self._location}/genre/podcasts"
            )
        )

    def _parse_podcast_ids(self, url):
        return (
            podcast_id
            for podcast_id in (
                self._parse_podcast_id(href)
                for href in self._parse_urls(_get_response(url).content)
                if href.startswith(
                    f"https://podcasts.apple.com/{self._location}/podcast/"
                )
            )
            if podcast_id
        )

    def _parse_urls(self, content):
        return (
            href
            for href in (el.attrib.get("href") for el in parse_xml(content, "a"))
            if href
        )

    def _parse_podcast_id(self, url):
        if match := _itunes_podcast_id_re.search(urlparse(url).path.split("/")[-1]):
            return match.group("id")
        return None


def _parse_feeds(json_data):
    for batch in batcher(_build_feeds_from_json(json_data), _batch_size):

        feeds_for_podcasts, feeds = itertools.tee(batch)

        podcasts = Podcast.objects.filter(
            rss__in={f.rss for f in feeds_for_podcasts}
        ).in_bulk(field_name="rss")

        feeds_for_insert, feeds = itertools.tee(
            (
                dataclasses.replace(feed, podcast=podcasts.get(feed.rss))
                for feed in feeds
            ),
        )

        Podcast.objects.bulk_create(
            (
                Podcast(title=feed.title, rss=feed.rss)
                for feed in feeds_for_insert
                if feed.podcast is None
            ),
            ignore_conflicts=True,
        )

        yield from feeds


def _get_response(url, data=None):
    response = requests.get(
        url,
        data,
        headers={"User-Agent": settings.USER_AGENT},
        timeout=10,
        allow_redirects=True,
    )
    response.raise_for_status()
    return response


def _build_feeds_from_json(json_data):
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
