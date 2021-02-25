import http

import pytest

from django.conf import settings
from django.urls import reverse

from radiofeed.episodes.factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
)
from radiofeed.podcasts.factories import SubscriptionFactory

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


class TestUserStats:
    def test_stats(self, client, login_user, podcast):
        SubscriptionFactory(podcast=podcast, user=login_user)
        AudioLogFactory(episode=EpisodeFactory(podcast=podcast), user=login_user)
        AudioLogFactory(episode=EpisodeFactory(podcast=podcast), user=login_user)
        AudioLogFactory(user=login_user)
        FavoriteFactory(user=login_user)
        resp = client.get(reverse("user_stats"))
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context["stats"]["subscriptions"] == 1
        assert resp.context["stats"]["listened"] == 3


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


class TestToggleDarkMode:
    def test_post_day_mode(self, client):
        client.cookies["dark-mode"] = "true"
        resp = client.post(reverse("toggle_dark_mode"))
        assert resp.url == "/"
        assert resp.cookies["dark-mode"].value == ""

    def test_post_night_mode(self, client):
        resp = client.post(reverse("toggle_dark_mode"))
        assert resp.url == "/"
        assert resp.cookies["dark-mode"].value == "true"
