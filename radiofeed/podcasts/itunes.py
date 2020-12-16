# Standard Library
import dataclasses
import json

# Django
from django.core.cache import cache

# Third Party Libraries
import requests

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

    def as_dict(self):
        return {
            "rss": self.rss,
            "title": self.title,
            "itunes": self.itunes,
            "image": self.image,
        }

    def as_json(self):
        return json.dumps(self.as_dict())


def fetch_itunes_genre(genre_id, num_results=20):
    """Fetch top rated results for genre"""
    return _get_search_results(
        {"term": "podcast", "limit": num_results, "genreId": genre_id,},
        cache_key=f"itunes:genre:{genre_id}",
    )


def search_itunes(search_term, num_results=12):
    """Does a search query on the iTunes API."""

    return _get_search_results(
        {"media": "podcast", "limit": num_results, "term": search_term,},
        cache_key=f"itunes:search:{search_term}",
    )


def _get_search_results(params, cache_key, cache_timeout=86400, requests_timeout=3):

    results = cache.get(cache_key)
    if results is None:
        try:
            response = requests.get(
                ITUNES_SEARCH_URL, params, verify=False, timeout=requests_timeout
            )
            response.raise_for_status()
            results = response.json()["results"]
            cache.set(cache_key, results, timeout=cache_timeout)
        except KeyError as e:
            raise Invalid from e
        except requests.exceptions.Timeout as e:
            raise Timeout from e
        except requests.RequestException as e:
            raise Invalid from e

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
