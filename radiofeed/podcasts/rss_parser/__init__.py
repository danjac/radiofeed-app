from typing import List

import requests

from lxml.etree import XMLSyntaxError
from pydantic import ValidationError

from radiofeed.episodes.models import Episode

from ..models import Podcast
from .exceptions import InvalidFeedError, RssParserError
from .feed_parser import parse_feed
from .headers import get_headers


def parse_rss(podcast: Podcast, force_update: bool = False) -> List[Episode]:
    """Fetches RSS and generates Feed. Checks etag header if we need to do an update.
    If any errors occur (e.g. RSS unavailable or invalid RSS) the error is saved in database
    and RssParserError raised.
    """

    try:
        head_response = requests.head(podcast.rss, headers=get_headers(), timeout=5)
        head_response.raise_for_status()
        if (
            (etag := head_response.headers.get("ETag", ""))
            and etag == podcast.etag
            and not force_update
        ):
            return []

        response = requests.get(
            podcast.rss, headers=get_headers(), stream=True, timeout=5
        )
        response.raise_for_status()
        return parse_feed(response.content).sync_podcast(podcast, etag, force_update)
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
