import pytest

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse, reverse_lazy

from radiofeed.common.asserts import assert_ok
from radiofeed.episodes.factories import (
    AudioLogFactory,
    BookmarkFactory,
    EpisodeFactory,
)
from radiofeed.podcasts.factories import PodcastFactory, SubscriptionFactory
from radiofeed.podcasts.models import Subscription
from radiofeed.users.models import User


class TestUserPreferences:
    url = reverse_lazy("users:preferences")

    def test_get(self, client, auth_user):
        response = client.get(self.url)
        assert_ok(response)

    def test_post(self, client, auth_user):
        response = client.post(
            self.url,
            {
                "send_email_notifications": False,
                "autoplay": True,
            },
        )

        assert_ok(response)

        auth_user.refresh_from_db()

        assert not auth_user.send_email_notifications


class TestUserStats:
    def test_stats(self, client, auth_user, podcast):

        SubscriptionFactory(podcast=podcast, user=auth_user)
        AudioLogFactory(episode=EpisodeFactory(podcast=podcast), user=auth_user)
        AudioLogFactory(episode=EpisodeFactory(podcast=podcast), user=auth_user)
        AudioLogFactory(user=auth_user)
        BookmarkFactory(user=auth_user)

        response = client.get(reverse("users:stats"))
        assert_ok(response)
        assert response.context["stats"]["subscribed"] == 1
        assert response.context["stats"]["listened"] == 3


class TestImportPodcastFeeds:
    url = reverse_lazy("users:import_podcast_feeds")

    @pytest.fixture
    def upload_file(self):
        return SimpleUploadedFile("feeds.opml", b"content", content_type="text/xml")

    def test_get(self, client, auth_user):
        assert_ok(client.get(self.url))

    def test_post_has_new_feeds(self, client, auth_user, mocker, upload_file):
        podcast = PodcastFactory()

        mocker.patch(
            "radiofeed.users.forms.OpmlUploadForm.parse_opml_feeds",
            return_value=[podcast.rss],
        )

        response = client.post(self.url, data={"opml": upload_file})

        assert_ok(response)

        assert response["HX-Redirect"] == reverse("podcasts:index")

        assert Subscription.objects.filter(user=auth_user, podcast=podcast).exists()

    def test_post_already_subscribed(self, client, auth_user, mocker, upload_file):
        subscription = SubscriptionFactory(user=auth_user)

        mocker.patch(
            "radiofeed.users.forms.OpmlUploadForm.parse_opml_feeds",
            return_value=[subscription.podcast.rss],
        )

        assert_ok(client.post(self.url, data={"opml": upload_file}))

        assert Subscription.objects.filter(user=auth_user).count() == 1

    def test_post_has_no_new_feeds(self, client, auth_user, mocker, upload_file):

        mocker.patch(
            "radiofeed.users.forms.OpmlUploadForm.parse_opml_feeds",
            return_value=["https://example.com/test.xml"],
        )

        assert_ok(client.post(self.url, data={"opml": upload_file}))

        assert not Subscription.objects.filter(user=auth_user).exists()

    def test_post_is_empty(self, client, auth_user, mocker, upload_file):

        mocker.patch(
            "radiofeed.users.forms.OpmlUploadForm.parse_opml_feeds",
            return_value=[],
        )

        assert_ok(client.post(self.url, data={"opml": upload_file}))

        assert not Subscription.objects.filter(user=auth_user).exists()


class TestExportPodcastFeeds:

    url = reverse_lazy("users:export_podcast_feeds")

    def test_page(self, client, auth_user):
        assert_ok(client.get(self.url))

    def test_export_opml(self, client, subscription):
        response = client.post(self.url)
        assert_ok(response)
        assert response["Content-Type"] == "application/xml"


class TestDeleteAccount:
    url = reverse_lazy("users:delete_account")

    def test_get(self, client, auth_user):
        # make sure we don't accidentally delete account on get request
        response = client.get(self.url)
        assert_ok(response)
        assert User.objects.exists()

    def test_post_unconfirmed(self, client, auth_user):
        response = client.post(self.url)
        assert_ok(response)
        assert User.objects.exists()

    def test_post_confirmed(self, client, auth_user):
        response = client.post(self.url, {"confirm-delete": True})
        assert response.url == settings.HOME_URL
        assert not User.objects.exists()
