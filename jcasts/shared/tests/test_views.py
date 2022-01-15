from django.urls import reverse

from jcasts.shared.asserts import assert_no_content, assert_ok


class TestRobots:
    def test_get(self, db, client, django_assert_num_queries):
        with django_assert_num_queries(1):
            assert_ok(client.get(reverse("robots")))


class TestSecurty:
    def test_get(self, db, client, django_assert_num_queries):
        with django_assert_num_queries(1):
            assert_ok(client.get(reverse("security")))


class TestAboutPages:
    def test_faq(self, db, client, django_assert_num_queries):
        with django_assert_num_queries(1):
            assert_ok(client.get(reverse("about:faq")))

    def test_credits(self, db, client, django_assert_num_queries):
        with django_assert_num_queries(1):
            assert_ok(client.get(reverse("about:credits")))

    def test_shortcuts(self, db, client, django_assert_num_queries):
        with django_assert_num_queries(1):
            assert_ok(client.get(reverse("about:shortcuts")))

    def test_terms(self, db, client, django_assert_num_queries):
        with django_assert_num_queries(1):
            assert_ok(client.get(reverse("about:terms")))


class TestAcceptCookies:
    def test_post(self, client, db, django_assert_num_queries):
        with django_assert_num_queries(1):
            resp = client.post(reverse("accept_cookies"))
        assert_no_content(resp)
        assert "accept-cookies" in resp.cookies


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
