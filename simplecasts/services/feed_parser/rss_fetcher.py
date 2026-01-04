import dataclasses
import hashlib
import http
from datetime import datetime

import httpx
from django.utils.functional import cached_property
from django.utils.http import http_date, quote_etag

from simplecasts.models import Podcast
from simplecasts.services.feed_parser.date_parser import parse_date
from simplecasts.services.feed_parser.exceptions import (
    DiscontinuedError,
    NotModifiedError,
    UnavailableError,
)
from simplecasts.services.http_client import Client


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
    Any other HTTP or network errors raise UnavailableError.
    """
    return _RSSFetcher(podcast=podcast).fetch(client)


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


@dataclasses.dataclass(kw_only=True)
class _RSSFetcher:
    podcast: Podcast

    accept = (
        "application/atom+xml,"
        "application/rdf+xml,"
        "application/rss+xml,"
        "application/x-netcdf,"
        "application/xml;q=0.9,"
        "text/xml;q=0.2,"
    )

    def fetch(self, client: Client) -> Response:
        try:
            try:
                response = Response(
                    response=client.get(
                        self.podcast.rss,
                        headers=self._build_http_headers(),
                    )
                )
                # Not all feeds use ETag or Last-Modified headers correctly,
                # so we also check the content hash to see if the feed has changed.
                if response.content_hash == self.podcast.content_hash:
                    raise NotModifiedError
                return response
            except httpx.HTTPStatusError as exc:
                match exc.response.status_code:
                    case http.HTTPStatus.GONE:
                        raise DiscontinuedError from exc
                    case http.HTTPStatus.NOT_MODIFIED:
                        raise NotModifiedError from exc
                    case _:
                        raise
        except httpx.HTTPError as exc:
            raise UnavailableError(str(exc)) from exc

    def _build_http_headers(self) -> dict[str, str]:
        """Returns headers to send with the HTTP request."""
        headers = {"Accept": self.accept}
        if self.podcast.etag:
            headers["If-None-Match"] = quote_etag(self.podcast.etag)
        if self.podcast.modified:
            headers["If-Modified-Since"] = http_date(self.podcast.modified.timestamp())
        return headers
