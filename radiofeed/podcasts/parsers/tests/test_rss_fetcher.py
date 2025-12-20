import datetime
import http

import httpx
import pytest

from radiofeed.http_client import Client
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.parsers.rss_fetcher import (
    DiscontinuedError,
    NotModifiedError,
    build_http_headers,
    fetch_rss,
    make_content_hash,
)


class TestMakeContentHash:
    def test_same(self):
        content = b"this is a test"
        assert make_content_hash(content) == make_content_hash(content)

    def test_empty(self):
        content = b""
        assert make_content_hash(content) == ""

    def test_spaces(self):
        content = b"this is a test   "
        assert make_content_hash(b"this is a test") == make_content_hash(content)

    def test_leading_spaces(self):
        content = b"   this is a test"
        assert make_content_hash(b"this is a test") == make_content_hash(content)

    def test_only_spaces(self):
        content = b"   \t  "
        assert make_content_hash(content) == ""

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
    url = "http://example.com/feed"

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
        response = fetch_rss(Podcast(rss=self.url), client)

        assert response.url == self.url
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
            fetch_rss(Podcast(rss=self.url, etag="123"), client)

    def test_content_not_modified(self):
        def _handle(request):
            return httpx.Response(
                http.HTTPStatus.OK,
                content=b"testvalue",
                request=request,
            )

        client = Client(transport=httpx.MockTransport(_handle))

        with pytest.raises(NotModifiedError):
            fetch_rss(
                Podcast(
                    rss=self.url,
                    content_hash=make_content_hash(b"testvalue"),
                ),
                client,
            )

    def test_gone(self):
        def _handle(request):
            return httpx.Response(http.HTTPStatus.GONE, request=request)

        client = Client(transport=httpx.MockTransport(_handle))
        with pytest.raises(DiscontinuedError):
            fetch_rss(Podcast(rss=self.url), client)

    def test_not_found(self):
        def _handle(request):
            return httpx.Response(http.HTTPStatus.NOT_FOUND, request=request)

        client = Client(transport=httpx.MockTransport(_handle))
        with pytest.raises(httpx.HTTPError):
            fetch_rss(Podcast(rss=self.url), client)

    def test_server_error(self):
        def _handle(request):
            return httpx.Response(
                http.HTTPStatus.INTERNAL_SERVER_ERROR, request=request
            )

        client = Client(transport=httpx.MockTransport(_handle))
        with pytest.raises(httpx.HTTPError):
            fetch_rss(Podcast(rss=self.url), client)
