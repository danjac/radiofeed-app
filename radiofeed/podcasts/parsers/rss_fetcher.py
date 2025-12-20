import dataclasses
import hashlib
import http
from datetime import datetime
from typing import Final

import httpx
from django.utils.functional import cached_property
from django.utils.http import http_date, quote_etag

from radiofeed.http_client import Client
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.parsers.date_parser import parse_date

_ACCEPT: Final = (
    "application/atom+xml,"
    "application/rdf+xml,"
    "application/rss+xml,"
    "application/x-netcdf,"
    "application/xml;q=0.9,"
    "text/xml;q=0.2,"
)


class DiscontinuedError(Exception):
    """Podcast has been marked discontinued and no longer available."""


class NotModifiedError(Exception):
    """RSS feed has not been modified since last update."""


@dataclasses.dataclass(kw_only=True, frozen=True)
class Response:
    """Wraps an HTTP response with convenient accessors for feed-related metadata."""

    response: httpx.Response

    @cached_property
    def content(self) -> bytes:
        """Returns the response content."""
        return self.response.content

    @cached_property
    def headers(self) -> httpx.Headers:
        """Returns the response headers."""
        return self.response.headers

    @cached_property
    def url(self) -> str:
        """Returns the final URL after any redirects."""
        return str(self.response.url)

    @cached_property
    def etag(self) -> str:
        """Returns the ETag header if available, otherwise an empty string."""
        return self.headers.get("ETag", "")

    @cached_property
    def modified(self) -> datetime | None:
        """Returns the Last-Modified header as a parsed datetime, or None if unavailable."""
        return parse_date(self.headers.get("Last-Modified"))

    @cached_property
    def content_hash(self) -> str:
        """Returns the SHA-256 hash of the response content, cached for efficiency."""
        return make_content_hash(self.content)


def fetch_rss(podcast: Podcast, client: Client) -> Response:
    """Fetches RSS or Atom feed.

    If the feed has not changed since the last fetch, raises NotModifiedError.
    If the feed has been discontinued (HTTP 410), raises DiscontinuedError.
    """
    try:
        response = Response(
            response=client.get(
                podcast.rss,
                headers=build_http_headers(
                    etag=podcast.etag,
                    modified=podcast.modified,
                ),
            )
        )
        # Not all feeds use ETag or Last-Modified headers correctly,
        # so we also check the content hash to see if the feed has changed.
        if response.content_hash == podcast.content_hash:
            raise NotModifiedError("Content not modified")
        return response
    except httpx.HTTPStatusError as exc:
        match exc.response.status_code:
            case http.HTTPStatus.GONE:
                raise DiscontinuedError("Discontinued") from exc
            case http.HTTPStatus.NOT_MODIFIED:
                raise NotModifiedError("Not Modified") from exc
            case _:
                raise


def build_http_headers(
    *,
    etag: str = "",
    modified: datetime | None = None,
) -> dict[str, str]:
    """Returns headers to send with the HTTP request."""
    headers = {"Accept": _ACCEPT}
    if etag:
        headers["If-None-Match"] = quote_etag(etag)
    if modified:
        headers["If-Modified-Since"] = http_date(modified.timestamp())
    return headers


def make_content_hash(content: bytes) -> str:
    """Hashes RSS content."""
    if not content:
        return ""

    # Use memoryview to avoid copying the content unnecessarily
    mv = memoryview(content)
    start = 0
    end = len(mv)

    whitespace = b" \t\r\n"

    while start < end and mv[start] in whitespace:
        start += 1

    while end > start and mv[end - 1] in whitespace:
        end -= 1

    if start == end:
        return ""

    return hashlib.sha256(mv[start:end]).hexdigest()
