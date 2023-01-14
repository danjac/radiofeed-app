from __future__ import annotations

import pathlib

import pytest

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse, reverse_lazy

from radiofeed.common.asserts import assert_ok
from radiofeed.common.factories import create_batch
from radiofeed.episodes.factories import create_audio_log, create_bookmark
from radiofeed.podcasts.factories import create_podcast, create_subscription
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
            },
            HTTP_HX_TARGET="preferences-form",
            HTTP_HX_REQUEST="true",
        )

        assert_ok(response)

        auth_user.refresh_from_db()

        assert not auth_user.send_email_notifications


class TestUserStats:
    def test_stats(self, client, auth_user):

        create_subscription(subscriber=auth_user)
        create_audio_log(user=auth_user)
        create_bookmark(user=auth_user)

        response = client.get(reverse("users:stats"))
        assert_ok(response)

    def test_stats_plural(self, client, auth_user):

        create_batch(create_audio_log, 3, user=auth_user)
        create_batch(create_bookmark, 3, user=auth_user)
        create_batch(create_subscription, 3, subscriber=auth_user)

        response = client.get(reverse("users:stats"))
        assert_ok(response)


class TestManagePodcastFeeds:
    def test_get(self, client, auth_user):
        assert_ok(client.get(reverse("users:manage_podcast_feeds")))


class TestImportPodcastFeeds:
    url = reverse_lazy("users:import_podcast_feeds")
    redirect_url = reverse_lazy("users:manage_podcast_feeds")

    @pytest.fixture
    def upload_file(self):
        return SimpleUploadedFile(
            "feeds.opml",
            (pathlib.Path(__file__).parent / "mocks" / "feeds.opml").read_bytes(),
            content_type="text/xml",
        )

    def test_post_has_new_feeds(self, client, auth_user, upload_file):
        podcast = create_podcast(
            rss="https://feeds.99percentinvisible.org/99percentinvisible"
        )

        assert_ok(
            client.post(
                self.url,
                data={"opml": upload_file},
                HTTP_HX_TARGET="import-feeds-form",
                HTTP_HX_REQUEST="true",
            ),
        )

        assert Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()

    def test_post_has_no_new_feeds(self, client, auth_user, mocker, upload_file):
        create_subscription(
            podcast=create_podcast(
                rss="https://feeds.99percentinvisible.org/99percentinvisible"
            ),
            subscriber=auth_user,
        )

        assert_ok(
            client.post(
                self.url,
                data={"opml": upload_file},
                HTTP_HX_TARGET="opml-import-form",
                HTTP_HX_REQUEST="true",
            ),
        )

        assert Subscription.objects.filter(subscriber=auth_user).exists()

    def test_post_is_empty(self, client, auth_user, mocker, upload_file):

        assert_ok(
            client.post(
                self.url,
                data={"opml": upload_file},
                HTTP_HX_TARGET="opml-import-form",
                HTTP_HX_REQUEST="true",
            ),
        )

        assert not Subscription.objects.filter(subscriber=auth_user).exists()

    def test_invalid_form(self, client, auth_user, mocker, upload_file):

        assert_ok(
            client.post(
                self.url,
                data={},
                HTTP_HX_TARGET="opml-import-form",
                HTTP_HX_REQUEST="true",
            ),
        )

        assert not Subscription.objects.filter(subscriber=auth_user).exists()


class TestExportPodcastFeeds:

    url = reverse_lazy("users:export_podcast_feeds")

    def test_export_opml(self, client, subscription):
        response = client.post(self.url)
        assert_ok(response)
        assert response["Content-Type"] == "text/x-opml"


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
        assert response.url == reverse("podcasts:landing_page")
        assert not User.objects.exists()
