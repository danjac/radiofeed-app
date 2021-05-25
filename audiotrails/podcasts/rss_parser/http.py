import requests

from requests.structures import CaseInsensitiveDict

from audiotrails.podcasts.rss_parser.headers import get_headers


def get_http_headers(url: str) -> CaseInsensitiveDict:
    response = requests.head(url, headers=get_headers(), timeout=5)
    response.raise_for_status()
    return response.headers


def get_http_response(url: str) -> requests.Response:
    response = requests.get(url, headers=get_headers(), stream=True, timeout=5)
    response.raise_for_status()
    return response
