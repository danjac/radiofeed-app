import dataclasses
import functools
import itertools
import re
from collections.abc import Iterator
from typing import Final
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from radiofeed import iterators
from radiofeed.podcasts.models import Podcast
from radiofeed.xml_parser import XMLParser

_ITUNES_LOCATIONS: Final = (
    "de",
    "fi",
    "fr",
    "gb",
    "se",
    "us",
)

_ITUNES_PODCAST_ID: Final = re.compile(r"id(?P<id>\d+)")


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


def search(search_term: str) -> list[Feed]:
    """Runs cached search for podcasts on iTunes API."""
    cache_key = search_cache_key(search_term)
    if (feeds := cache.get(cache_key)) is None:
        feeds = list(
            _parse_feeds(
                "https://itunes.apple.com/search",
                {
                    "term": search_term,
                    "media": "podcast",
                },
            )
        )
        cache.set(cache_key, feeds)
    return feeds


def search_cache_key(search_term: str) -> str:
    """Cache key based on search term."""
    return "itunes:" + urlsafe_base64_encode(force_bytes(search_term, "utf-8"))


def crawl() -> Iterator[Feed]:
    """Crawls iTunes podcast catalog and creates new Podcast instances from any new
    feeds found."""
    for location in _ITUNES_LOCATIONS:
        yield from Crawler(location).crawl()


class Crawler:
    """Crawls iTunes podcast catalog.

    Args:
        location: country location e.g. "us"
    """

    def __init__(self, location: str):
        self._location = location
        self._feed_ids: set[str] = set()
        self._parser = _itunes_parser()

    def crawl(self) -> Iterator[Feed]:
        """Crawls through location and finds new feeds, adding any new podcasts to the
        database."""
        for url in self._parse_genre_urls():
            yield from self._parse_genre_url(url)

    def _parse_genre_urls(self) -> list[str]:
        try:
            return [
                href
                for href in self._parse_urls(
                    _get_response(
                        f"https://itunes.apple.com/{self._location}/genre/podcasts/id26",
                        allow_redirects=True,
                    ).content
                )
                if href.startswith(
                    f"https://podcasts.apple.com/{self._location}/genre/podcasts"
                )
            ]
        except requests.RequestException:
            return []

    def _parse_genre_url(self, url: str) -> Iterator[Feed]:
        for feed_ids in iterators.batcher(self._parse_podcast_ids(url), 100):
            yield from self._parse_feeds(feed_ids)

    def _parse_feeds(self, feed_ids: list[str]) -> Iterator[Feed]:
        try:
            _feed_ids: set[str] = set(feed_ids) - self._feed_ids

            yield from _parse_feeds(
                "https://itunes.apple.com/lookup",
                {
                    "id": ",".join(_feed_ids),
                    "entity": "podcast",
                },
            )

            self._feed_ids = self._feed_ids.union(_feed_ids)
        except requests.RequestException:
            return

    def _parse_podcast_ids(self, url: str) -> list[str]:
        try:
            return [
                podcast_id
                for podcast_id in (
                    self._parse_podcast_id(href)
                    for href in self._parse_urls(
                        _get_response(url, allow_redirects=True).content
                    )
                    if href.startswith(
                        f"https://podcasts.apple.com/{self._location}/podcast/"
                    )
                )
                if podcast_id
            ]
        except requests.RequestException:
            return []

    def _parse_urls(self, content: bytes) -> Iterator[str]:
        for element in self._parser.iterparse(
            content, "{http://www.apple.com/itms/}html", "/apple:html"
        ):
            try:
                yield from self._parser.itertext(element, "//a//@href")
            finally:
                element.clear()

    def _parse_podcast_id(self, url: str) -> str | None:
        if match := _ITUNES_PODCAST_ID.search(urlparse(url).path.split("/")[-1]):
            return match.group("id")
        return None


def _get_response(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    **kwargs,
) -> requests.Response:
    response = requests.get(
        url,
        params=params,
        headers=(headers or {}) | {"User-Agent": settings.USER_AGENT},
        timeout=10,
        **kwargs,
    )
    response.raise_for_status()
    return response


def _parse_feeds(url: str, params: dict | None = None) -> Iterator[Feed]:
    for batch in iterators.batcher(
        _build_feeds_from_json(
            _get_response(
                url,
                params,
                headers={"Accept": "application/json"},
            ).json()
        ),
        100,
    ):
        feeds_for_podcasts, feeds = itertools.tee(batch)

        podcasts = Podcast.objects.filter(
            rss__in={f.rss for f in feeds_for_podcasts},
            private=False,
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


@functools.cache
def _itunes_parser() -> XMLParser:
    """Returns cached XMLParser instance."""
    return XMLParser({"apple": "http://www.apple.com/itms/"})
