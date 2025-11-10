import hashlib
from typing import Final

import httpx
from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from pydantic import BaseModel, Field, ValidationError

from radiofeed.http_client import Client
from radiofeed.podcasts.models import Podcast

COUNTRIES: Final = (
    "ae",
    "ag",
    "ai",
    "am",
    "ao",
    "ar",
    "at",
    "au",
    "az",
    "ba",
    "bb",
    "be",
    "bg",
    "bh",
    "bj",
    "bm",
    "bo",
    "br",
    "bs",
    "bt",
    "bw",
    "by",
    "bz",
    "ca",
    "cd",
    "cg",
    "ch",
    "ci",
    "cl",
    "cm",
    "cn",
    "co",
    "cr",
    "cv",
    "cy",
    "cz",
    "de",
    "dk",
    "dm",
    "do",
    "ec",
    "ee",
    "eg",
    "es",
    "fi",
    "fj",
    "fm",
    "fr",
    "ga",
    "gb",
    "gd",
    "ge",
    "gh",
    "gm",
    "gr",
    "gt",
    "gw",
    "gy",
    "hk",
    "hn",
    "hr",
    "hu",
    "id",
    "ie",
    "il",
    "in",
    "iq",
    "is",
    "it",
    "jm",
    "jo",
    "jp",
    "ke",
    "kg",
    "kh",
    "kn",
    "kr",
    "kw",
    "ky",
    "kz",
    "la",
    "lb",
    "lc",
    "lk",
    "lr",
    "lt",
    "lu",
    "lv",
    "ly",
    "ma",
    "md",
    "me",
    "mg",
    "mk",
    "ml",
    "mm",
    "mn",
    "mo",
    "mr",
    "ms",
    "mt",
    "mu",
    "mv",
    "mw",
    "mx",
    "my",
    "mz",
    "na",
    "ne",
    "ng",
    "ni",
    "nl",
    "no",
    "np",
    "nz",
    "om",
    "pa",
    "pe",
    "pg",
    "ph",
    "pl",
    "pt",
    "py",
    "qa",
    "ro",
    "rs",
    "ru",
    "rw",
    "sa",
    "sb",
    "sc",
    "se",
    "sg",
    "si",
    "sk",
    "sl",
    "sn",
    "sr",
    "sv",
    "sz",
    "tc",
    "td",
    "th",
    "tj",
    "tm",
    "tn",
    "to",
    "tr",
    "tt",
    "tw",
    "tz",
    "ua",
    "ug",
    "uy",
    "uz",
    "vc",
    "ve",
    "vg",
    "vn",
    "vu",
    "xk",
    "ye",
    "za",
    "zm",
    "zw",
)


class ItunesError(Exception):
    """iTunes API error."""


class Feed(BaseModel):
    """Encapsulates iTunes API result."""

    rss: str = Field(..., alias="feedUrl")
    url: str = Field(..., alias="collectionViewUrl")
    title: str = Field(..., alias="collectionName")
    image: str = Field(..., alias="artworkUrl100")

    def __str__(self) -> str:
        """Returns title of feed"""
        return self.title


def search(
    client: Client,
    search_term: str,
    *,
    limit: int = settings.DEFAULT_PAGE_SIZE,
) -> list[Feed]:
    """Search iTunes podcast API. New podcasts will be added to the database."""
    if feeds := _fetch_feeds(
        client,
        "https://itunes.apple.com/search",
        {
            "term": search_term,
            "limit": limit,
            "media": "podcast",
        },
    ):
        Podcast.objects.bulk_create(
            (
                Podcast(
                    rss=feed.rss,
                    title=feed.title,
                )
                for feed in feeds
            ),
            ignore_conflicts=True,
        )

    return feeds


def search_cached(
    client: Client,
    search_term: str,
    *,
    limit: int = settings.DEFAULT_PAGE_SIZE,
    cache_timeout: int = settings.DEFAULT_CACHE_TIMEOUT,
) -> list[Feed]:
    """Search iTunes podcast API. Results are cached."""
    cache_key = _get_cache_key(search_term, limit)
    feeds = cache.get(cache_key, None)
    if feeds is None:
        feeds = search(client, search_term, limit=limit)
        cache.set(cache_key, feeds, timeout=cache_timeout)
    return feeds


def fetch_chart(
    client: Client,
    country: str,
    *,
    limit: int,
    **fields,
) -> list[Feed]:
    """Fetch top chart from iTunes podcast API. Any new podcasts will be added."""

    url = f"https://rss.marketingtools.apple.com/api/v2/{country}/podcasts/top/{limit}/podcasts.json"
    itunes_ids = _fetch_itunes_ids(client, url)

    if not itunes_ids:
        return []

    if feeds := _fetch_feeds(
        client,
        "https://itunes.apple.com/lookup",
        {
            "id": ",".join(itunes_ids),
        },
    ):
        urls = _get_canonical_urls(feeds)
        podcasts = (Podcast(rss=url, **fields) for url in urls)

        if fields:
            Podcast.objects.bulk_create(
                podcasts,
                unique_fields=["rss"],
                update_conflicts=True,
                update_fields=fields,
            )
        else:
            Podcast.objects.bulk_create(podcasts, ignore_conflicts=True)

    return feeds


def _fetch_feeds(client: Client, url: str, params: dict) -> list[Feed]:
    """Fetches and parses feeds from iTunes API."""
    return [
        feed
        for feed in (
            _parse_feed(result)
            for result in _fetch_json(client, url, params).get("results", [])
        )
        if feed
    ]


def _fetch_itunes_ids(client: Client, url: str) -> set[str]:
    """Fetches podcast IDs from results."""
    return {
        itunes_id
        for itunes_id in (
            result.get("id")
            for result in _fetch_json(client, url).get("feed", {}).get("results", [])
        )
        if itunes_id
    }


def _fetch_json(client: Client, url: str, params: dict | None = None) -> dict:
    """Fetches JSON response from the given URL."""
    try:
        return client.get(
            url,
            params=params or {},
            headers={"Accept": "application/json"},
        ).json()
    except httpx.HTTPError as exc:
        raise ItunesError(str(exc)) from exc


def _parse_feed(feed: dict) -> Feed | None:
    """Parses a single feed entry."""
    try:
        return Feed(**feed)
    except ValidationError:
        return None


def _get_canonical_urls(feeds: list[Feed]) -> set[str]:
    """Returns a list of canonical URLs for the given feeds."""

    # make sure we fetch only unique feeds in the right order
    urls = dict.fromkeys(feed.rss for feed in feeds).keys()

    # in certain cases, we may have duplicates in the database
    canonical_urls = dict(
        Podcast.objects.filter(
            duplicates__rss__in=urls,
        ).values_list("rss", "canonical")
    )

    return {canonical_urls.get(url, url) for url in urls}


def _get_cache_key(search_term: str, limit: int) -> str:
    value = search_term.strip().casefold()
    digest = hashlib.sha256(force_bytes(value)).digest()
    encoded = urlsafe_base64_encode(digest).rstrip("=")
    return f"itunes:{encoded}:{limit}"
