from __future__ import annotations

import dataclasses

import requests

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.template.defaultfilters import striptags
from django.utils.encoding import force_str
from django.utils.functional import cached_property

from audiotrails.podcasts.models import Category, Podcast
from audiotrails.shared.template.defaulttags import unescape

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"


class Timeout(requests.exceptions.Timeout):
    pass


class Invalid(requests.RequestException):
    pass


@dataclasses.dataclass
class SearchResult:
    rss: str
    itunes: str
    title: str
    image: str
    podcast: Podcast | None = None

    @cached_property
    def cleaned_title(self) -> str:
        return striptags(unescape(self.title))


def fetch_itunes_genre(
    genre_id: int, num_results: int = settings.DEFAULT_ITUNES_LIMIT
) -> tuple[list[SearchResult], list[Podcast]]:
    """Fetch top rated results for genre"""
    return _get_or_create_podcasts(
        _get_search_results(
            {
                "term": "podcast",
                "limit": num_results,
                "genreId": genre_id,
            },
            cache_key=f"itunes:genre:{genre_id}",
        )
    )


def search_itunes(
    search_term: str, num_results: int = settings.DEFAULT_ITUNES_LIMIT
) -> tuple[list[SearchResult], list[Podcast]]:
    """Does a search query on the iTunes API."""

    return _get_or_create_podcasts(
        _get_search_results(
            {
                "media": "podcast",
                "limit": num_results,
                "term": force_str(search_term),
            },
            cache_key=f"itunes:search:{search_term}",
        )
    )


def crawl_itunes(limit: int) -> int:
    categories = Category.objects.filter(itunes_genre_id__isnull=False).order_by("name")
    new_podcasts = 0

    for category in categories:
        podcasts: list[Podcast] = []

        try:
            results, podcasts = fetch_itunes_genre(
                category.itunes_genre_id, num_results=limit
            )
        except (Invalid, Timeout):
            continue

        new_podcasts += len(podcasts)
    return new_podcasts


def _get_or_create_podcasts(
    results: list[SearchResult],
) -> tuple[list[SearchResult], list[Podcast]]:
    """Looks up podcast associated with result. Optionally adds new podcasts if not found"""

    podcasts = Podcast.objects.filter(
        Q(itunes__in=[r.itunes for r in results]) | Q(rss__in=[r.rss for r in results])
    ).in_bulk(field_name="rss")

    new_podcasts = []
    for result in results:
        result.podcast = podcasts.get(result.rss, None)
        if result.podcast is None:
            new_podcasts.append(
                Podcast(title=result.title, rss=result.rss, itunes=result.itunes)
            )

    if new_podcasts:
        Podcast.objects.bulk_create(new_podcasts, ignore_conflicts=True)

    return results, new_podcasts


def _get_search_results(
    params: dict[str, str | int],
    cache_key: str,
    cache_timeout: int = 86400,
    requests_timeout: int = 3,
) -> list[SearchResult]:

    if results := cache.get(cache_key):
        return results

    try:
        response = requests.get(
            ITUNES_SEARCH_URL,
            params,
            timeout=requests_timeout,
            verify=True,
        )
        response.raise_for_status()
        results = _make_search_results(response.json()["results"])
        cache.set(cache_key, results, timeout=cache_timeout)
        return results
    except requests.exceptions.Timeout as e:
        raise Timeout from e

    except (KeyError, requests.RequestException) as e:
        raise Invalid from e


def _make_search_results(results: list[dict[str, str]]) -> list[SearchResult]:
    return [
        SearchResult(
            item["feedUrl"],
            item["trackViewUrl"],
            item["collectionName"],
            item["artworkUrl600"],
        )
        for item in results
        if "feedUrl" in item
    ]
