import datetime
import http

import httpx
import pytest

from radiofeed.feedparser.exceptions import (
    InaccessibleError,
    NotModifiedError,
    UnavailableError,
)
from radiofeed.feedparser.rss_fetcher import (
    build_http_headers,
    fetch_rss,
    make_content_hash,
)
from radiofeed.http_client import Client


class TestMakeContentHash:
    def test_same(self):
        content = b"this is a test"
        assert make_content_hash(content) == make_content_hash(content)

    def test_different(self):
        content_a = b"this is a test"
        content_b = b"this is another test"
        assert make_content_hash(content_a) != make_content_hash(content_b)


class TestBuildHttpHeaders:
    def test_with_etag(self):
        headers = build_http_headers(etag="123", modified=None)
        assert headers["If-None-Match"] == '"123"'

    def test_with_modified(self):
        headers = build_http_headers(
            etag="",
            modified=datetime.datetime(2025, 1, 1),
        )
        assert headers["If-Modified-Since"] == "Wed, 01 Jan 2025 00:00:00 GMT"


class TestFetchRss:
    def test_ok(self):
        def _handle(request):
            return httpx.Response(
                http.HTTPStatus.OK,
                content=b"test",
                request=request,
                headers={
                    "ETag": "123",
                    "Last-Modified": "Fri, 01 Jan 2025 00:00:00 GMT",
                },
            )

        client = Client(transport=httpx.MockTransport(_handle))
        response = fetch_rss(client, "http://example.com")

        assert response.url == "http://example.com"
        assert response.etag == "123"
        assert response.modified == datetime.datetime(
            2025, 1, 1, 0, 0, tzinfo=datetime.UTC
        )
        assert response.content == b"test"
        assert response.content_hash == make_content_hash(b"test")

    def test_not_modified(self):
        def _handle(request):
            return httpx.Response(
                http.HTTPStatus.NOT_MODIFIED,
                content=b"",
                request=request,
                headers={
                    "ETag": "123",
                    "Last-Modified": "Fri, 01 Jan 2025 00:00:00 GMT",
                },
            )

        client = Client(transport=httpx.MockTransport(_handle))
        with pytest.raises(NotModifiedError):
            fetch_rss(client, "http://example.com", etag="123")

    def test_not_found(self):
        def _handle(request):
            return httpx.Response(http.HTTPStatus.NOT_FOUND, request=request)

        client = Client(transport=httpx.MockTransport(_handle))
        with pytest.raises(InaccessibleError):
            fetch_rss(client, "http://example.com")

    def test_server_error(self):
        def _handle(request):
            return httpx.Response(
                http.HTTPStatus.INTERNAL_SERVER_ERROR, request=request
            )

        client = Client(transport=httpx.MockTransport(_handle))
        with pytest.raises(UnavailableError):
            fetch_rss(client, "http://example.com")
