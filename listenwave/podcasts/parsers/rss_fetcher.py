import hashlib
import http
from datetime import datetime
from typing import Final

import httpx
from django.utils.functional import cached_property
from django.utils.http import http_date, quote_etag

from listenwave.http_client import Client
from listenwave.podcasts.parsers.date_parser import parse_date
from listenwave.podcasts.parsers.exceptions import (
    DiscontinuedError,
    NotModifiedError,
    UnavailableError,
)

_ACCEPT: Final = (
    "application/atom+xml,"
    "application/rdf+xml,"
    "application/rss+xml,"
    "application/x-netcdf,"
    "application/xml;q=0.9,"
    "text/xml;q=0.2,"
)

_WHITESPACE: Final = b" \t\r\n"


class Response:
    """Wraps an HTTP response with convenient accessors for feed-related metadata."""

    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    @cached_property
    def content(self) -> bytes:
        """Returns the response content."""
        return self._response.content

    @cached_property
    def headers(self) -> httpx.Headers:
        """Returns the response headers."""
        return self._response.headers

    @cached_property
    def url(self) -> str:
        """Returns the final URL after any redirects."""
        return str(self._response.url)

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


def fetch_rss(
    client: Client,
    url: str,
    *,
    etag: str = "",
    modified: datetime | None = None,
) -> Response:
    """Fetches RSS or Atom feed."""
    try:
        try:
            headers = build_http_headers(etag=etag, modified=modified)
            return Response(client.get(url, headers=headers))
        except httpx.HTTPStatusError as exc:
            match exc.response.status_code:
                case http.HTTPStatus.GONE:
                    raise DiscontinuedError(response=exc.response) from exc
                case http.HTTPStatus.NOT_MODIFIED:
                    raise NotModifiedError(response=exc.response) from exc
                case _:
                    raise
    except httpx.HTTPError as exc:
        raise UnavailableError from exc


def build_http_headers(
    *,
    etag: str,
    modified: datetime | None,
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

    while start < end and mv[start] in _WHITESPACE:
        start += 1

    while end > start and mv[end - 1] in _WHITESPACE:
        end -= 1

    if start == end:
        return ""

    return hashlib.sha256(mv[start:end]).hexdigest()
