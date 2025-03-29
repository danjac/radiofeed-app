import dataclasses
from collections.abc import Iterable
from typing import Final

import httpx
from django.core.cache import cache
from django.db.models import Q
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from radiofeed.http_client import Client
from radiofeed.podcasts.models import Podcast

COUNTRIES: Final = (
    "ae",
    "ag",
    "ai",
    "al",
    "am",
    "ao",
    "ar",
    "at",
    "au",
    "az",
    "ba",
    "bb",
    "be",
    "bf",
    "bg",
    "bh",
    "bj",
    "bm",
    "bn",
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
    "dz",
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
    "nr",
    "nz",
    "om",
    "pa",
    "pe",
    "pg",
    "ph",
    "pk",
    "pl",
    "pt",
    "pw",
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
    "st",
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
    "us",
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


class ItunesError(ValueError):
    """Base class for iTunes API errors."""


@dataclasses.dataclass(frozen=True)
class Feed:
    """Encapsulates iTunes API result."""

    rss: str
    url: str
    title: str = ""
    image: str = ""

    def __str__(self) -> str:
        """Return title or RSS"""
        return self.title or self.rss

    def __hash__(self) -> int:
        """Hash based on RSS."""
        return hash(self.rss)


def search(client: Client, search_term: str, *, limit: int = 30) -> list[Feed]:
    """Search iTunes podcast API. New podcasts will be added.
    If the feed already exists, it will be attached to the Feed."""
    feeds = _fetch_feeds(
        client,
        "https://itunes.apple.com/search",
        term=search_term,
        limit=limit,
        media="podcast",
    )

    if not feeds:
        return []

    _insert_podcasts(feeds)
    return feeds


def search_cached(
    client: Client,
    search_term: str,
    *,
    limit: int = 30,
    cache_timeout: int = 300,
) -> list[Feed]:
    """Search iTunes podcast API with caching."""
    search_term = search_term.strip().casefold()
    cache_key = search_cache_key(search_term, limit)

    if (feeds := cache.get(cache_key)) is None:
        feeds = search(client, search_term, limit=limit)
        cache.set(cache_key, feeds, cache_timeout)

    return feeds


def search_cache_key(search_term: str, limit: int) -> str:
    """Properly encoded search cache key"""
    return f"search-itunes:{urlsafe_base64_encode(force_bytes(search_term))}:{limit}"


def fetch_chart(
    client: Client,
    *,
    country: str = "gb",
    limit: int = 30,
    promote: bool = True,
) -> list[Feed]:
    """Fetch top chart from iTunes podcast API. Any new podcasts will be added.
    All podcasts in the chart will be promoted.
    """

    if country not in COUNTRIES:
        raise ItunesError(f"Invalid country code: {country}")

    feeds: list[Feed] = []

    if itunes_ids := _fetch_itunes_ids(
        client,
        f"https://rss.marketingtools.apple.com/api/v2/{country}/podcasts/top/{limit}/podcasts.json",
    ):
        feeds = _fetch_feeds(
            client,
            "https://itunes.apple.com/lookup",
            id=",".join(itunes_ids),
        )

        if promote:
            _promote_podcasts(feeds)
        else:
            _insert_podcasts(feeds)
    return feeds


def _fetch_feeds(client: Client, url: str, **params) -> list[Feed]:
    """Fetches and parses feeds from iTunes API."""
    return _dedupe(
        [
            feed
            for feed in [
                _parse_feed(result)
                for result in _fetch_json(client, url, **params).get("results", [])
            ]
            if feed
        ]
    )


def _fetch_itunes_ids(client: Client, url: str, **params) -> list[str]:
    """Fetches podcast IDs from results."""
    return _dedupe(
        [
            itunes_id
            for itunes_id in [
                result.get("id")
                for result in _fetch_json(client, url, **params)
                .get("feed", {})
                .get("results", [])
            ]
            if itunes_id
        ]
    )


def _fetch_json(client: Client, url: str, **params) -> dict:
    """Fetches JSON response from the given URL."""
    try:
        response = client.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
        )
        return response.json()
    except httpx.HTTPError as e:
        raise ItunesError(f"Failed to fetch {url}: {e}") from e


def _parse_feed(feed: dict) -> Feed | None:
    """Parses a single feed entry."""
    try:
        return Feed(
            rss=feed["feedUrl"],
            url=feed["collectionViewUrl"],
            title=feed["collectionName"],
            image=feed["artworkUrl100"],
        )
    except KeyError:
        return None


def _insert_podcasts(feeds: list[Feed]) -> None:
    # add new podcasts
    Podcast.objects.bulk_create(
        [Podcast(rss=feed.rss, title=feed.title) for feed in feeds],
        ignore_conflicts=True,
    )


def _promote_podcasts(feeds: list[Feed]) -> None:
    rss_feeds = {feed.rss for feed in feeds}

    q = Q(rss__in=rss_feeds) | Q(duplicates__rss__in=rss_feeds)

    # check duplicates
    rss_feeds |= set(Podcast.objects.filter(q).values_list("rss", flat=True))

    # add new podcasts
    Podcast.objects.bulk_create(
        [Podcast(rss=rss, promoted=True) for rss in rss_feeds],
        unique_fields=["rss"],
        update_fields=["promoted"],
        update_conflicts=True,
    )

    # demote podcasts not in the chart
    Podcast.objects.filter(promoted=True).exclude(q).update(promoted=False)


def _dedupe(items: Iterable) -> list:
    return list(dict.fromkeys(items))
