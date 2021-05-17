import http

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from audiotrails.episodes.factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
)
from audiotrails.podcasts.factories import FollowFactory, PodcastFactory

from ..factories import UserFactory

User = get_user_model()


class UserPreferencesTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_get(self) -> None:
        resp = self.client.get(reverse("user_preferences"))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)

    def test_post(self) -> None:
        url = reverse("user_preferences")
        resp = self.client.post(url, {"send_recommendations_email": False})
        self.assertRedirects(resp, url)
        self.user.refresh_from_db()
        assert not self.user.send_recommendations_email


class UserStatsTests(TestCase):
    def test_stats(self) -> None:
        podcast = PodcastFactory()
        user = UserFactory()
        self.client.force_login(user)

        FollowFactory(podcast=podcast, user=user)
        AudioLogFactory(episode=EpisodeFactory(podcast=podcast), user=user)
        AudioLogFactory(episode=EpisodeFactory(podcast=podcast), user=user)
        AudioLogFactory(user=user)
        FavoriteFactory(user=user)
        resp = self.client.get(reverse("user_stats"))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp.context["stats"]["follows"], 1)
        self.assertEqual(resp.context["stats"]["listened"], 3)


class ExportPodcastFeedsTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.podcast = PodcastFactory()

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_get(self) -> None:
        resp = self.client.get(reverse("export_podcast_feeds"))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)

    def test_export_opml(self) -> None:
        FollowFactory(podcast=self.podcast, user=self.user)
        resp = self.client.post(reverse("export_podcast_feeds"), {"format": "opml"})
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp["Content-Type"], "application/xml")

    def test_export_csv(self) -> None:
        FollowFactory(podcast=self.podcast, user=self.user)
        resp = self.client.post(reverse("export_podcast_feeds"), {"format": "csv"})
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp["Content-Type"], "text/csv")


class DeleteAccountTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def test_get(self) -> None:
        # make sure we don't accidentally delete account on get request
        resp = self.client.get(reverse("delete_account"))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertTrue(User.objects.exists())

    def test_post_unconfirmed(self) -> None:
        resp = self.client.post(reverse("delete_account"))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertTrue(User.objects.exists())

    def test_post_confirmed(self) -> None:
        resp = self.client.post(reverse("delete_account"), {"confirm-delete": True})
        self.assertRedirects(resp, settings.HOME_URL)
        self.assertFalse(User.objects.exists())


class AcceptCookiesTests(TestCase):
    def test_post(self) -> None:
        resp = self.client.post(reverse("accept_cookies"))
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertIn("accept-cookies", resp.cookies)
