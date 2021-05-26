from __future__ import annotations

from datetime import datetime

import requests

from django.core.validators import ValidationError
from lxml.etree import XMLSyntaxError
from requests.structures import CaseInsensitiveDict

from audiotrails.episodes.models import Episode
from audiotrails.podcasts.models import Podcast
from audiotrails.podcasts.rss_parser import http
from audiotrails.podcasts.rss_parser.date_parser import parse_date
from audiotrails.podcasts.rss_parser.exceptions import InvalidFeedError, RssParserError
from audiotrails.podcasts.rss_parser.feed_parser import parse_feed_from_url


def parse_rss(podcast: Podcast, force_update: bool = False) -> list[Episode]:
    """Fetches RSS and generates Feed. Checks etag header if we need to do an update.
    If any errors occur (e.g. RSS unavailable or invalid RSS) the error is saved in database
    and RssParserError raised.
    """

    try:
        headers = http.get_headers(podcast.rss)

        etag = headers.get("ETag", "")
        last_modified = get_last_modified_date(headers)

        if not should_update(podcast, etag, last_modified, force_update):
            return []

        return parse_feed_from_url(podcast.rss).sync_podcast(
            podcast,
            force_update,
            extra_kwargs={"etag": etag},
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


def get_last_modified_date(headers: CaseInsensitiveDict) -> datetime | None:
    """Finds suitable date header"""
    for header in ("Last-Modified", "Date"):
        if value := parse_date(headers.get(header, None)):
            return value
    return None


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
