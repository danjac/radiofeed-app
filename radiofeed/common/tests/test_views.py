from __future__ import annotations

import requests

from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from radiofeed.common.asserts import assert_bad_request, assert_ok


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
        return reverse("cover_image", args=[size, url])

    def encode_url(self, url):
        return urlsafe_base64_encode(force_bytes(url))

    def test_ok(self, client, db, mocker):
        class MockResponse:
            content = b"content"

            def raise_for_status(self):
                pass

        mocker.patch("requests.get", return_value=MockResponse())
        mocker.patch("PIL.Image.open", return_value=mocker.Mock())
        assert_ok(client.get(self.get_url(100, self.encode_url(self.cover_url))))

    def test_bad_encoded_url(self, client, db):
        assert_bad_request(client.get(self.get_url(100, "bad string")))

    def test_failed_download(self, client, db, mocker):
        class MockResponse:
            def raise_for_status(self):
                raise requests.HTTPError("OOPS")

        mocker.patch("requests.get", return_value=MockResponse())
        assert_bad_request(
            client.get(self.get_url(100, self.encode_url(self.cover_url)))
        )

    def test_failed_process(self, client, db, mocker):
        class MockResponse:
            content = b"content"

            def raise_for_status(self):
                pass

        mocker.patch("requests.get", return_value=MockResponse())
        mocker.patch("PIL.Image.open", side_effect=IOError())
        assert_bad_request(client.get(self.get_url(100, self.cover_url.encode().hex())))


class TestErrorPages:
    def test_bad_request(self, db, client):
        assert_ok(client.get(reverse("error:bad_request")))

    def test_not_found(self, db, client):
        assert_ok(client.get(reverse("error:not_found")))

    def test_forbidden(self, db, client):
        assert_ok(client.get(reverse("error:forbidden")))

    def test_not_allowed(self, db, client):
        assert_ok(client.get(reverse("error:not_allowed")))

    def test_server_error(self, db, client):
        assert_ok(client.get(reverse("error:server_error")))

    def test_csrf(self, db, client):
        assert_ok(client.get(reverse("error:csrf_error")))
