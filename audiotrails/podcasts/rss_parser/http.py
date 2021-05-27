from __future__ import annotations

import dataclasses
import random

from datetime import datetime

import requests

from audiotrails.podcasts.rss_parser.date_parser import parse_date

USER_AGENTS: list[str] = [
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/57.0.2987.110 "
        "Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/61.0.3163.79 "
        "Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:55.0) "
        "Gecko/20100101 "
        "Firefox/55.0"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/61.0.3163.91 "
        "Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/62.0.3202.89 "
        "Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/63.0.3239.108 "
        "Safari/537.36"
    ),
]


@dataclasses.dataclass
class Headers:
    etag: str = ""
    last_modified: datetime | None = None
    date: datetime | None = None


def get_headers(url: str) -> Headers:
    """Returns common timestamp headers from HEAD"""
    response = requests.head(url, headers=fake_user_agent_headers(), timeout=5)
    response.raise_for_status()

    return Headers(
        etag=response.headers.get("Etag", ""),
        last_modified=parse_date(response.headers.get("Last-Modified", None)),
        date=parse_date(response.headers.get("Date", None)),
    )


def get_response(url: str) -> requests.Response:
    response = requests.get(
        url, headers=fake_user_agent_headers(), stream=True, timeout=5
    )
    response.raise_for_status()
    return response


def fake_user_agent_headers() -> dict[str, str]:
    """Return randomized user agent in case only browser clients allowed."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
