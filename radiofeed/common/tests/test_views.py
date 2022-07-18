from __future__ import annotations

from django.urls import reverse

from radiofeed.common.asserts import assert_ok


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
        assert_ok(client.get(reverse("error:csrf")))
