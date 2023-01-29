from __future__ import annotations

import urllib.parse

import requests

from django.core.signing import Signer
from django.shortcuts import render
from django.urls import reverse

from radiofeed.asserts import assert_not_found, assert_ok


class TestManifest:
    def test_get(self, db, client):
        assert_ok(client.get(reverse("manifest")))


class TestServiceWorker:
    def test_get(self, db, client):
        assert_ok(client.get(reverse("service_worker")))


class TestFavicon:
    def test_get(self, db, client):
        assert_ok(client.get(reverse("favicon")))


class TestRobots:
    def test_get(self, db, client):
        assert_ok(client.get(reverse("robots")))


class TestSecurty:
    def test_get(self, db, client):
        assert_ok(client.get(reverse("security")))


class TestAbout:
    def test_get(self, db, client):
        assert_ok(client.get(reverse("about")))


class TestAcceptCookies:
    def test_post(self, client, db):
        response = client.post(reverse("accept_cookies"))
        assert_ok(response)
        assert "accept-cookies" in response.cookies


class TestCoverImage:
    cover_url = "http://example.com/test.png"

    def get_url(self, size, url):
        return (
            reverse("cover_image", kwargs={"size": size})
            + "?"
            + urllib.parse.urlencode({"url": url})
        )

    def encode_url(self, url):
        return Signer().sign(url)

    def test_ok(self, client, db, mocker):
        class MockResponse:
            content = b"content"

            def raise_for_status(self):
                pass

        mocker.patch("requests.get", return_value=MockResponse())
        mocker.patch("PIL.Image.open", return_value=mocker.Mock())
        assert_ok(client.get(self.get_url(100, self.encode_url(self.cover_url))))

    def test_not_accepted_size(self, client, db, mocker):
        assert_not_found(client.get(self.get_url(500, self.encode_url(self.cover_url))))

    def test_missing_url_param(self, client, db, mocker):
        assert_not_found(client.get(reverse("cover_image", kwargs={"size": 100})))

    def test_unsigned_url(self, client, db):
        assert_not_found(client.get(self.get_url(100, self.cover_url)))

    def test_failed_download(self, client, db, mocker):
        class MockResponse:
            def raise_for_status(self):
                raise requests.RequestException("OOPS")

        mocker.patch("requests.get", return_value=MockResponse())
        assert_ok(client.get(self.get_url(100, self.encode_url(self.cover_url))))

    def test_failed_process(self, client, db, mocker):
        class MockResponse:
            content = b"content"

            def raise_for_status(self):
                pass

        mocker.patch("requests.get", return_value=MockResponse())
        mocker.patch("PIL.Image.open", side_effect=IOError())
        assert_ok(client.get(self.get_url(100, self.encode_url(self.cover_url))))


class TestErrorPages:
    def test_bad_request(self, db, rf):
        assert_ok(render(rf.get("/"), "400.html"))

    def test_not_found(self, db, rf):
        assert_ok(render(rf.get("/"), "404.html"))

    def test_forbidden(self, db, rf):
        assert_ok(render(rf.get("/"), "403.html"))

    def test_not_allowed(self, db, rf):
        assert_ok(render(rf.get("/"), "405.html"))

    def test_server_error(self, db, rf):
        assert_ok(render(rf.get("/"), "500.html"))

    def test_csrf(self, db, rf):
        assert_ok(render(rf.get("/"), "403_csrf.html"))
