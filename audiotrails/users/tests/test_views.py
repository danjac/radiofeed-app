from django.conf import settings
from django.urls import reverse

from audiotrails.episodes.factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
)
from audiotrails.podcasts.factories import FollowFactory
from audiotrails.shared.assertions import assert_ok


class TestUserPreferences:
    def test_get(self, client, auth_user):
        resp = client.get(reverse("user_preferences"))
        assert_ok(resp)

    def test_post(self, client, auth_user):
        url = reverse("user_preferences")
        resp = client.post(
            url,
            {
                "send_recommendations_email": False,
                "autoplay": True,
            },
        )
        assert resp.url == url

        auth_user.refresh_from_db()

        assert auth_user.autoplay
        assert not auth_user.send_recommendations_email


class TestUserStats:
    def test_stats(self, client, auth_user, podcast):

        FollowFactory(podcast=podcast, user=auth_user)
        AudioLogFactory(episode=EpisodeFactory(podcast=podcast), user=auth_user)
        AudioLogFactory(episode=EpisodeFactory(podcast=podcast), user=auth_user)
        AudioLogFactory(user=auth_user)
        FavoriteFactory(user=auth_user)

        resp = client.get(reverse("user_stats"))
        assert_ok(resp)
        assert resp.context["stats"]["follows"] == 1
        assert resp.context["stats"]["listened"] == 3


class TestExportPodcastFeeds:
    def test_get(self, client, auth_user):
        resp = client.get(reverse("export_podcast_feeds"))
        assert_ok(resp)

    def test_export_opml(self, client, follow):
        resp = client.post(reverse("export_podcast_feeds"), {"format": "opml"})
        assert_ok(resp)
        assert resp["Content-Type"] == "application/xml"

    def test_export_csv(self, client, follow):
        resp = client.post(reverse("export_podcast_feeds"), {"format": "csv"})
        assert_ok(resp)
        assert resp["Content-Type"] == "text/csv"


class TestDeleteAccount:
    def test_get(self, client, auth_user, django_user_model):
        # make sure we don't accidentally delete account on get request
        resp = client.get(reverse("delete_account"))
        assert_ok(resp)
        assert django_user_model.objects.exists()

    def test_post_unconfirmed(self, client, auth_user, django_user_model):
        resp = client.post(reverse("delete_account"))
        assert_ok(resp)
        assert django_user_model.objects.exists()

    def test_post_confirmed(self, client, auth_user, django_user_model):
        resp = client.post(reverse("delete_account"), {"confirm-delete": True})
        assert resp.url == settings.HOME_URL
        assert not django_user_model.objects.exists()


class TestAcceptCookies:
    def test_post(self, client, db):
        resp = client.post(reverse("accept_cookies"))
        assert_ok(resp)
        assert "accept-cookies" in resp.cookies
