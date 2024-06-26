import http
import pathlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertRedirects

from radiofeed.episodes.tests.factories import AudioLogFactory, BookmarkFactory
from radiofeed.podcasts.models import Subscription
from radiofeed.podcasts.tests.factories import PodcastFactory, SubscriptionFactory
from radiofeed.users.models import User


class TestUserPreferences:
    url = reverse_lazy("users:preferences")

    @pytest.mark.django_db()
    def test_get(self, client, auth_user):
        response = client.get(self.url, HTTP_HX_REQUEST="true")
        assert response.status_code == http.HTTPStatus.OK

    @pytest.mark.django_db()
    def test_post(self, client, auth_user):
        response = client.post(
            self.url,
            {
                "send_email_notifications": False,
            },
        )
        assert response.url == self.url

        auth_user.refresh_from_db()

        assert not auth_user.send_email_notifications

    @pytest.mark.django_db()
    def test_post_not_htmx(self, client, auth_user):
        assertRedirects(
            client.post(
                self.url,
                {
                    "send_email_notifications": False,
                },
            ),
            self.url,
        )

        auth_user.refresh_from_db()

        assert not auth_user.send_email_notifications


class TestUserStats:
    @pytest.mark.django_db()
    def test_stats(self, client, auth_user):
        SubscriptionFactory(subscriber=auth_user)
        AudioLogFactory(user=auth_user)
        BookmarkFactory(user=auth_user)

        response = client.get(reverse("users:stats"))
        assert response.status_code == http.HTTPStatus.OK

    @pytest.mark.django_db()
    def test_stats_plural(self, client, auth_user):
        AudioLogFactory.create_batch(3, user=auth_user)
        BookmarkFactory.create_batch(3, user=auth_user)
        SubscriptionFactory.create_batch(3, subscriber=auth_user)
        response = client.get(reverse("users:stats"))
        assert response.status_code == http.HTTPStatus.OK


class TestManagePodcastFeeds:
    @pytest.mark.django_db()
    def test_get(self, client, auth_user):
        SubscriptionFactory(subscriber=auth_user)

        response = client.get(reverse("users:manage_podcast_feeds"))
        assert response.status_code == http.HTTPStatus.OK


class TestImportPodcastFeeds:
    url = reverse_lazy("users:import_podcast_feeds")
    redirect_url = reverse_lazy("users:manage_podcast_feeds")

    @pytest.fixture()
    def upload_file(self):
        return SimpleUploadedFile(
            "feeds.opml",
            (pathlib.Path(__file__).parent / "mocks" / "feeds.opml").read_bytes(),
            content_type="text/xml",
        )

    @pytest.mark.django_db()
    def test_post_has_new_feeds(self, client, auth_user, upload_file):
        podcast = PodcastFactory(
            rss="https://feeds.99percentinvisible.org/99percentinvisible"
        )

        response = client.post(
            self.url,
            data={"opml": upload_file},
        )
        assert response.url == reverse("users:manage_podcast_feeds")
        assert Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()

    @pytest.mark.django_db()
    def test_post_invalid_form(self, client, auth_user):
        response = client.post(
            self.url,
            data={"opml": "test.xml"},
            HTTP_HX_TARGET="import-feeds-form",
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == http.HTTPStatus.OK

        assert not Subscription.objects.filter(subscriber=auth_user).exists()

    @pytest.mark.django_db()
    def test_post_podcast_not_in_db(self, client, auth_user, upload_file):
        response = client.post(
            self.url,
            data={"opml": upload_file},
            HTTP_HX_TARGET="import-feeds-form",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == http.HTTPStatus.OK

        assert Subscription.objects.filter(subscriber=auth_user).count() == 0

    @pytest.mark.django_db()
    def test_post_has_no_new_feeds(self, client, auth_user, upload_file):
        SubscriptionFactory(
            podcast=PodcastFactory(
                rss="https://feeds.99percentinvisible.org/99percentinvisible"
            ),
            subscriber=auth_user,
        )

        response = client.post(
            self.url,
            data={"opml": upload_file},
            HTTP_HX_TARGET="opml-import-form",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == http.HTTPStatus.OK

        assert Subscription.objects.filter(subscriber=auth_user).exists()

    @pytest.mark.django_db()
    def test_post_is_empty(self, client, auth_user, upload_file):
        response = client.post(
            self.url,
            data={"opml": upload_file},
            HTTP_HX_TARGET="opml-import-form",
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == http.HTTPStatus.OK
        assert not Subscription.objects.filter(subscriber=auth_user).exists()


class TestExportPodcastFeeds:
    url = reverse_lazy("users:export_podcast_feeds")

    @pytest.mark.django_db()
    def test_export_opml(self, client, subscription):
        response = client.get(self.url)
        assert response["Content-Type"] == "text/x-opml"


class TestDeleteAccount:
    url = reverse_lazy("users:delete_account")

    @pytest.mark.django_db()
    def test_get(self, client, auth_user):
        # make sure we don't accidentally delete account on get request
        response = client.get(self.url)
        assert response.status_code == http.HTTPStatus.OK
        assert User.objects.exists()

    @pytest.mark.django_db()
    def test_post_unconfirmed(self, client, auth_user):
        response = client.get(self.url)
        assert response.status_code == http.HTTPStatus.OK
        assert User.objects.exists()

    @pytest.mark.django_db()
    def test_post_confirmed(self, client, auth_user):
        response = client.post(self.url, {"confirm-delete": True})
        assert response.url == reverse("podcasts:index")
        assert not User.objects.exists()
