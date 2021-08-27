from django.urls import reverse

from jcasts.shared.assertions import assert_ok


class TestHomePage:
    def test_anonymous(self, db, client):
        resp = client.get(reverse("home_page"))
        assert_ok(resp)

    def test_authenticated(self, client, auth_user):
        resp = client.get(reverse("home_page"))
        assert resp.url == reverse("podcasts:index")


class TestRobots:
    def test_robots(self, db, client):
        assert_ok(client.get(reverse("robots")))


class TestAboutPages:
    def test_credits(self, db, client):
        assert_ok(client.get(reverse("about:credits")))

    def test_help(self, db, client):
        assert_ok(client.get(reverse("about:help")))

    def test_privacy(self, db, client):
        assert_ok(client.get(reverse("about:privacy")))


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


class TestAcceptCookies:
    def test_post(self, client, db):
        resp = client.post(reverse("accept_cookies"))
        assert_ok(resp)
        assert "accept-cookies" in resp.cookies
