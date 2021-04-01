import requests

from lxml.etree import XMLSyntaxError
from pydantic import ValidationError

from .date_parser import parse_date
from .exceptions import InvalidFeedError, RssParserError
from .feed_parser import parse_feed
from .headers import get_headers


def parse_rss(podcast, force_update=False):
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


def get_last_modified_date(headers):
    for header in ("Last-Modified", "Date"):
        if value := parse_date(headers.get(header, None)):
            return value
    return None


def should_update(podcast, etag, last_modified, force_update):
    if force_update or not podcast.pub_date:
        return True
    if etag and etag != podcast.etag:
        return True
    if last_modified and last_modified > podcast.pub_date:
        return True
    return False
