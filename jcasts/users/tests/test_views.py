from django.conf import settings
from django.urls import reverse, reverse_lazy

from jcasts.episodes.factories import AudioLogFactory, EpisodeFactory, FavoriteFactory
from jcasts.podcasts.factories import FollowFactory
from jcasts.shared.assertions import assert_ok


class TestUserPreferences:
    url = reverse_lazy("users:preferences")

    def test_get(self, client, auth_user, django_assert_num_queries):
        with django_assert_num_queries(3):
            resp = client.get(self.url)
        assert_ok(resp)

    def test_post(self, client, auth_user, django_assert_num_queries):
        with django_assert_num_queries(4):
            resp = client.post(
                self.url,
                {
                    "send_recommendations_email": False,
                    "autoplay": True,
                },
            )
        assert resp.url == self.url

        auth_user.refresh_from_db()

        assert auth_user.autoplay
        assert not auth_user.send_recommendations_email


class TestUserStats:
    def test_stats(self, client, auth_user, podcast, django_assert_num_queries):

        FollowFactory(podcast=podcast, user=auth_user)
        AudioLogFactory(episode=EpisodeFactory(podcast=podcast), user=auth_user)
        AudioLogFactory(episode=EpisodeFactory(podcast=podcast), user=auth_user)
        AudioLogFactory(user=auth_user)
        FavoriteFactory(user=auth_user)

        with django_assert_num_queries(9):
            resp = client.get(reverse("users:stats"))
        assert_ok(resp)
        assert resp.context["stats"]["follows"] == 1
        assert resp.context["stats"]["listened"] == 3


class TestExportPodcastFeeds:
    url = reverse_lazy("users:export_podcast_feeds")

    def test_get(self, client, auth_user, django_assert_num_queries):
        with django_assert_num_queries(3):
            assert_ok(client.get(self.url))

    def test_export_opml(self, client, follow, django_assert_num_queries):
        with django_assert_num_queries(4):
            resp = client.post(self.url, {"format": "opml"})
        assert_ok(resp)
        assert resp["Content-Type"] == "application/xml"

    def test_export_csv(self, client, follow, django_assert_num_queries):
        with django_assert_num_queries(4):
            resp = client.post(self.url, {"format": "csv"})
        assert_ok(resp)
        assert resp["Content-Type"] == "text/csv"


class TestDeleteAccount:
    url = reverse_lazy("users:delete_account")

    def test_get(self, client, auth_user, django_user_model, django_assert_num_queries):
        # make sure we don't accidentally delete account on get request
        with django_assert_num_queries(3):
            resp = client.get(self.url)
        assert_ok(resp)
        assert django_user_model.objects.exists()

    def test_post_unconfirmed(
        self, client, auth_user, django_user_model, django_assert_num_queries
    ):
        with django_assert_num_queries(3):
            resp = client.post(self.url)
        assert_ok(resp)
        assert django_user_model.objects.exists()

    def test_post_confirmed(
        self, client, auth_user, django_user_model, django_assert_num_queries
    ):
        with django_assert_num_queries(16):
            resp = client.post(self.url, {"confirm-delete": True})
        assert resp.url == settings.HOME_URL
        assert not django_user_model.objects.exists()
