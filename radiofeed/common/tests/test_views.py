from __future__ import annotations

import httpx

from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from radiofeed.common.asserts import assert_bad_request, assert_ok
from radiofeed.common.views import static_page


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
        return reverse("cover_image", kwargs={"encoded_url": url, "size": size})

    def encode_url(self, url):
        return urlsafe_base64_encode(force_bytes(url))

    def test_ok(self, client, db, mocker):
        class MockResponse:
            content = b"content"

            def raise_for_status(self):
                pass

        mocker.patch("httpx.get", return_value=MockResponse())
        mocker.patch("PIL.Image.open", return_value=mocker.Mock())
        assert_ok(client.get(self.get_url(100, self.encode_url(self.cover_url))))

    def test_not_accepted_size(self, client, db, mocker):
        assert_bad_request(
            client.get(self.get_url(500, self.encode_url(self.cover_url)))
        )

    def test_bad_encoded_url(self, client, db):
        assert_bad_request(client.get(self.get_url(100, "bad string")))

    def test_invalid_url(self, client, db):
        assert_bad_request(client.get(self.get_url(100, self.encode_url("bad string"))))

    def test_failed_download(self, client, db, mocker):
        class MockResponse:
            def raise_for_status(self):
                raise httpx.HTTPError("OOPS")

        mocker.patch("httpx.get", return_value=MockResponse())
        assert_bad_request(
            client.get(self.get_url(100, self.encode_url(self.cover_url)))
        )

    def test_failed_process(self, client, db, mocker):
        class MockResponse:
            content = b"content"

            def raise_for_status(self):
                pass

        mocker.patch("httpx.get", return_value=MockResponse())
        mocker.patch("PIL.Image.open", side_effect=IOError())
        assert_bad_request(
            client.get(self.get_url(100, self.encode_url(self.cover_url)))
        )


class TestErrorPages:
    def test_bad_request(self, db, rf):
        assert_ok(static_page(rf.get("/"), "400.html"))

    def test_not_found(self, db, rf):
        assert_ok(static_page(rf.get("/"), "404.html"))

    def test_forbidden(self, db, rf):
        assert_ok(static_page(rf.get("/"), "403.html"))

    def test_not_allowed(self, db, rf):
        assert_ok(static_page(rf.get("/"), "405.html"))

    def test_server_error(self, db, rf):
        assert_ok(static_page(rf.get("/"), "500.html"))

    def test_csrf(self, db, rf):
        assert_ok(static_page(rf.get("/"), "403_csrf.html"))
