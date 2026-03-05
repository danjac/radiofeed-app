import dataclasses
import hashlib
import http
from typing import TYPE_CHECKING

import aiohttp
from django.utils.functional import cached_property
from django.utils.http import http_date, quote_etag

from radiofeed.podcasts.feed_parser.date_parser import parse_date
from radiofeed.podcasts.feed_parser.exceptions import (
    DiscontinuedError,
    NotModifiedError,
    UnavailableError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

    from radiofeed.client import Client, ClientResponse
    from radiofeed.podcasts.models import Podcast


@dataclasses.dataclass(kw_only=True, frozen=True)
class Response:
    """Wraps a ClientResponse with convenient accessors for feed-related metadata."""

    client_response: ClientResponse

    @property
    def content(self) -> bytes:
        """Returns the response body."""
        return self.client_response.content

    @property
    def url(self) -> str:
        """Returns the response URL."""
        return self.client_response.url

    @property
    def headers(self) -> Mapping[str, str]:
        """Returns the response headers."""
        return self.client_response.headers

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


async def fetch_rss(podcast: Podcast, client: Client) -> Response:
    """Fetches RSS or Atom feed.

    If the feed has not changed since the last fetch, raises NotModifiedError.
    If the feed has been discontinued (HTTP 410), raises DiscontinuedError.
    Any other HTTP or network errors raise UnavailableError.
    """
    return await _RSSFetcher(podcast=podcast).fetch(client)


def make_content_hash(content: bytes) -> str:
    """Hashes RSS content."""
    if not content:
        return ""

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

    async def fetch(self, client: Client) -> Response:
        try:
            try:
                aio_response = await client.get(
                    self.podcast.rss,
                    headers=self._build_http_headers(),
                )
                if aio_response.status == http.HTTPStatus.NOT_MODIFIED:
                    raise NotModifiedError
                response = Response(client_response=aio_response)
                if response.content_hash == self.podcast.content_hash:
                    raise NotModifiedError
                return response
            except aiohttp.ClientResponseError as exc:
                match exc.status:
                    case http.HTTPStatus.GONE:
                        raise DiscontinuedError from exc
                    case _:
                        raise
        except aiohttp.ClientError as exc:
            raise UnavailableError(str(exc)) from exc

    def _build_http_headers(self) -> dict[str, str]:
        """Returns headers to send with the HTTP request."""
        headers = {"Accept": self.accept}
        if self.podcast.etag:
            headers["If-None-Match"] = quote_etag(self.podcast.etag)
        if self.podcast.modified:
            headers["If-Modified-Since"] = http_date(self.podcast.modified.timestamp())
        return headers
