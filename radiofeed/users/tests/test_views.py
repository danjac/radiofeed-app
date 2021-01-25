# Standard Library
import http

# Django
from django.conf import settings
from django.urls import reverse

# Third Party Libraries
import pytest

pytestmark = pytest.mark.django_db


class TestUserPreferences:
    def test_get(self, client, login_user):
        resp = client.get(reverse("user_preferences"))
        assert resp.status_code == http.HTTPStatus.OK

    def test_post(self, client, login_user):
        url = reverse("user_preferences")
        resp = client.post(url, {"send_recommendations_email": False})
        assert resp.url == url
        login_user.refresh_from_db()
        assert not login_user.send_recommendations_email


class TestDeleteAccount:
    def test_get(self, client, login_user, user_model):
        # make sure we don't accidentally delete account on get request
        resp = client.get(reverse("delete_account"))
        assert resp.status_code == http.HTTPStatus.OK
        assert user_model.objects.exists()

    def test_post_unconfirmed(self, client, login_user, user_model):
        resp = client.post(reverse("delete_account"))
        assert resp.status_code == http.HTTPStatus.OK
        assert user_model.objects.exists()

    def test_post_confirmed(self, client, login_user, user_model):
        resp = client.post(reverse("delete_account"), {"confirm-delete": True})
        assert resp.url == settings.HOME_URL
        assert not user_model.objects.exists()


class TestAcceptCookies:
    def test_post(self, client):
        resp = client.post(reverse("accept_cookies"))
        assert resp.status_code == http.HTTPStatus.OK
        assert "accept-cookies" in resp.cookies
