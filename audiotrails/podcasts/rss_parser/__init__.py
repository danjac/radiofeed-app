from __future__ import annotations

from datetime import datetime

import requests

from django.core.validators import ValidationError
from lxml.etree import XMLSyntaxError

from audiotrails.episodes.models import Episode
from audiotrails.podcasts.models import Podcast
from audiotrails.podcasts.rss_parser.date_parser import get_last_modified_date
from audiotrails.podcasts.rss_parser.exceptions import InvalidFeedError, RssParserError
from audiotrails.podcasts.rss_parser.feed_parser import parse_feed_from_url
from audiotrails.podcasts.rss_parser.headers import get_headers


def parse_rss(podcast: Podcast, force_update: bool = False) -> list[Episode]:
    """Fetches RSS and generates Feed. Checks etag header if we need to do an update.
    If any errors occur (e.g. RSS unavailable or invalid RSS) the error is saved in database
    and RssParserError raised.
    """

    try:
        head_response = requests.head(podcast.rss, headers=get_headers(), timeout=5)
        head_response.raise_for_status()

        etag = head_response.headers.get("ETag", "")
        last_modified = get_last_modified_date(head_response.headers)

        if not should_update(podcast, etag, last_modified, force_update):
            return []

        return parse_feed_from_url(podcast.rss).sync_podcast(
            podcast, etag, force_update
        )
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


def should_update(
    podcast: Podcast, etag: str, last_modified: datetime | None, force_update: bool
) -> bool:
    """Does preliminary check based on headers to determine whether to update this podcast.
    We also check the feed date info, but this is an optimization so we don't have to parse
    the RSS first."""
    return bool(
        force_update
        or podcast.pub_date is None
        or (etag and etag != podcast.etag)
        or (last_modified and last_modified > podcast.pub_date),
    )
