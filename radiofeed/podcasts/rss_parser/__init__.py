from typing import Optional, Tuple

import requests

from lxml.etree import XMLSyntaxError
from pydantic import ValidationError

from ..models import Podcast
from .feed_parser import InvalidFeedError, parse_feed
from .headers import get_headers
from .models import Feed


class RssParserError(Exception):
    ...


def parse_rss(podcast: Podcast, *, force_update: bool = False) -> int:
    """Parses RSS feed for podcast. If force_update is provided will
    re-fetch all podcast info, episodes etc even if podcast does not
    have new content (provided a valid feed is available).

    Returns number of new episodes.
    """

    feed, etag = fetch_rss_feed(podcast, force_update)
    if feed is None:
        return 0

    return len(feed.sync_podcast(podcast, etag, force_update))


def fetch_rss_feed(podcast: Podcast, force_update: bool) -> Tuple[Optional[Feed], str]:
    """Fetches RSS and generates Feed. Checks etag header if we need to do an update.
    If any errors occur (e.g. RSS unavailable or invalid RSS) the error is saved in database
    and RssParserError raised.
    """

    try:
        etag = fetch_etag(podcast.rss)
        if etag and etag == podcast.etag and not force_update:
            return None, etag

        response = requests.get(
            podcast.rss, headers=get_headers(), stream=True, timeout=5
        )
        response.raise_for_status()
        return parse_feed(response.content), etag
    except (
        InvalidFeedError,
        ValidationError,
        XMLSyntaxError,
        requests.RequestException,
    ) as e:
        podcast.sync_error = str(e)
        podcast.num_retries += 1
        podcast.save()

        raise RssParserError(podcast.sync_error) from e


def fetch_etag(url: str) -> str:
    # fetch etag and last modified
    head_response = requests.head(url, headers=get_headers(), timeout=5)
    head_response.raise_for_status()
    headers = head_response.headers
    return headers.get("ETag", "")
