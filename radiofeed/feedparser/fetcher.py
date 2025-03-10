import hashlib
from typing import Final

import httpx
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.http import http_date, quote_etag

from radiofeed.feedparser.date_parser import parse_date
from radiofeed.feedparser.exceptions import (
    InaccessibleError,
    NotModifiedError,
    UnavailableError,
)
from radiofeed.http_client import Client

_ACCEPT: Final = (
    "application/atom+xml,"
    "application/rdf+xml,"
    "application/rss+xml,"
    "application/x-netcdf,"
    "application/xml;q=0.9,"
    "text/xml;q=0.2,"
)


class Response:
    """Wraps an HTTP response with convenient accessors for feed-related metadata."""

    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    @cached_property
    def url(self) -> str:
        """Returns the URL of the response."""
        return str(self._response.url)

    @cached_property
    def etag(self) -> str:
        """Returns the ETag header if available, otherwise an empty string."""
        return self._response.headers.get("ETag", "")

    @cached_property
    def modified(self) -> timezone.datetime | None:
        """Returns the Last-Modified header as a parsed datetime, or None if unavailable."""
        return parse_date(self._response.headers.get("Last-Modified"))

    @cached_property
    def content(self) -> bytes:
        """Returns the response content as bytes."""
        return self._response.content

    @cached_property
    def content_hash(self) -> str:
        """Returns the SHA-256 hash of the response content, cached for efficiency."""
        return make_content_hash(self.content)


def fetch(
    client: Client,
    url: str,
    *,
    etag: str = "",
    modified: timezone.datetime | None = None,
) -> Response:
    """Fetches the podcast's RSS or Atom feed."""
    try:
        try:
            return Response(
                client.get(
                    url,
                    headers=build_http_headers(etag=etag, modified=modified),
                )
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.is_redirect:
                raise NotModifiedError(response=exc.response) from exc
            if exc.response.is_client_error:
                raise InaccessibleError(response=exc.response) from exc
            raise
    except httpx.HTTPError as exc:
        raise UnavailableError from exc


def build_http_headers(
    *,
    etag: str,
    modified: timezone.datetime | None,
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
    return hashlib.sha256(content).hexdigest()
