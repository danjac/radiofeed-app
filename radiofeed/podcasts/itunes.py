import dataclasses
import itertools
import re
from collections.abc import Iterator
from typing import Final
from urllib.parse import urlparse

import httpx
import lxml
from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from radiofeed import iterators
from radiofeed.podcasts.models import Podcast
from radiofeed.xml_parser import XMLParser

_ITUNES_LOCALES: Final = (
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
        response = httpx.get(
            "https://itunes.apple.com/search",
            params={
                "term": search_term,
                "media": "podcast",
            },
            headers={
                "Accept": "application/json",
                "User-Agent": settings.USER_AGENT,
            },
            timeout=10,
        )
        response.raise_for_status()
        feeds = list(_parse_feeds(response))
        cache.set(cache_key, feeds)
    return feeds


def search_cache_key(search_term: str) -> str:
    """Cache key based on search term."""
    return "itunes:" + urlsafe_base64_encode(force_bytes(search_term, "utf-8"))


def crawl() -> Iterator[Feed]:
    """Crawls iTunes podcast catalog and creates new Podcast instances from any new
    feeds found."""

    parser = XMLParser({"apple": "http://www.apple.com/itms/"})

    with httpx.Client(
        headers={
            "User-Agent": settings.USER_AGENT,
        }
    ) as client:
        for locale in _ITUNES_LOCALES:
            yield from ItunesLocaleParser(
                client=client,
                parser=parser,
                locale=locale,
            ).parse()


class ItunesLocaleParser:
    """Parses feeds from specific locale."""

    def __init__(self, *, client: httpx.Client, parser: XMLParser, locale: str):
        self._client = client
        self._parser = parser
        self._locale = locale

    def parse(self) -> Iterator[Feed]:
        """Parses feeds from specific locale."""
        for feed_ids in iterators.batcher(self._parse_feed_ids(), 100):
            try:
                yield from _parse_feeds(
                    self._get_response(
                        "https://itunes.apple.com/lookup",
                        params={
                            "id": ",".join(feed_ids),
                            "entity": "podcast",
                        },
                        headers={
                            "Accept": "application/json",
                        },
                    )
                )
            except httpx.HTTPError:
                continue

    def _parse_feed_ids(self) -> Iterator[str]:
        for url in self._parse_urls(
            f"https://itunes.apple.com/{self._locale}/genre/podcasts/id26",
            f"https://podcasts.apple.com/{self._locale}/genre/podcasts",
        ):
            yield from self._parse_feed_ids_in_category(url)

    def _parse_feed_ids_in_category(self, url: str) -> Iterator[str]:
        for href in self._parse_urls(
            url,
            f"https://podcasts.apple.com/{self._locale}/podcast/",
        ):
            if feed_id := _parse_feed_id(href):
                yield feed_id

    def _parse_urls(self, url: str, startswith: str) -> Iterator[str]:
        try:
            response = self._get_response(url, follow_redirects=True)
            for element in self._parser.iterparse(
                response.content, "{http://www.apple.com/itms/}html", "/apple:html"
            ):
                try:
                    for url in self._parser.itertext(element, "//a//@href"):
                        if url.startswith(startswith):
                            yield url
                finally:
                    element.clear()
        except (httpx.HTTPError, lxml.etree.XMLSyntaxError):
            return

    def _get_response(
        self,
        url,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: int = 10,
        **kwargs,
    ):
        response = self._client.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout,
            **kwargs,
        )
        response.raise_for_status()
        return response


def _parse_feed_id(url: str) -> str | None:
    if match := _ITUNES_PODCAST_ID.search(urlparse(url).path.split("/")[-1]):
        return match.group("id")
    return None


def _parse_feeds(
    response: httpx.Response,
) -> Iterator[Feed]:
    for batch in iterators.batcher(
        _build_feeds_from_json(response.json()),
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
                for feed in set(feeds_for_insert)
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
