import dataclasses
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
    PermanentHTTPError,
    TemporaryHTTPError,
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
    def status_code(self) -> int:
        """Returns the HTTP status code of the response."""
        return self.response.status_code

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


def fetch_rss(client: Client, url: str, **headers) -> Response:
    """Fetches RSS or Atom feed."""
    try:
        try:
            return Response(
                response=client.get(
                    url,
                    headers=build_http_headers(**headers),
                )
            )
        except httpx.HTTPStatusError as exc:
            match exc.response.status_code:
                case http.HTTPStatus.GONE:
                    cls = DiscontinuedError
                case http.HTTPStatus.NOT_MODIFIED:
                    cls = NotModifiedError
                case (
                    http.HTTPStatus.BAD_REQUEST
                    | http.HTTPStatus.FORBIDDEN
                    | http.HTTPStatus.METHOD_NOT_ALLOWED
                    | http.HTTPStatus.NOT_ACCEPTABLE
                    | http.HTTPStatus.NOT_FOUND
                    | http.HTTPStatus.UNAUTHORIZED
                    | http.HTTPStatus.UNAVAILABLE_FOR_LEGAL_REASONS
                ):
                    cls = PermanentHTTPError
                case _:
                    cls = TemporaryHTTPError
            message = http.HTTPStatus(exc.response.status_code).phrase
            raise cls(message, response=exc.response) from exc
    except httpx.HTTPError as exc:
        raise TemporaryHTTPError(str(exc)) from exc


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

    while start < end and mv[start] in _WHITESPACE:
        start += 1

    while end > start and mv[end - 1] in _WHITESPACE:
        end -= 1

    if start == end:
        return ""

    return hashlib.sha256(mv[start:end]).hexdigest()
