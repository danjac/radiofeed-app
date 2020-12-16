# Standard Library
import dataclasses
import json

# Third Party Libraries
import requests

ITUNES_SEARCH_URL = "https://itunes.apple.com/search/"


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


def search_itunes(search_term, num_results=12):
    """Does a search query on the iTunes API."""
    params = {
        "media": "podcast",
        "term": search_term,
    }

    try:
        response = requests.get(ITUNES_SEARCH_URL, params, verify=False, timeout=3)
        response.raise_for_status()
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
        for item in response.json()["results"][:num_results]
        if "feedUrl" in item
    ]
