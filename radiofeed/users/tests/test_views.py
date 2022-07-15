from __future__ import annotations

import pathlib

import pytest

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import get_template
from django.urls import reverse, reverse_lazy

from radiofeed.episodes.factories import (
    AudioLogFactory,
    BookmarkFactory,
    EpisodeFactory,
)
from radiofeed.podcasts.factories import PodcastFactory, SubscriptionFactory
from radiofeed.podcasts.models import Subscription
from radiofeed.users.factories import EmailAddressFactory
from radiofeed.users.models import User


class TestUserPreferences:
    url = reverse_lazy("users:preferences")

    def test_get(self, client, auth_user, assert_ok):
        response = client.get(self.url)
        assert_ok(response)

    def test_post(self, client, auth_user, assert_ok):
        response = client.post(
            self.url,
            {
                "send_email_notifications": False,
                "autoplay": True,
            },
            HTTP_HX_TARGET="preferences-form",
        )

        assert_ok(response)

        auth_user.refresh_from_db()

        assert not auth_user.send_email_notifications


class TestUserStats:
    def test_stats(self, client, auth_user, podcast, assert_ok):

        SubscriptionFactory(podcast=podcast, user=auth_user)
        AudioLogFactory(episode=EpisodeFactory(podcast=podcast), user=auth_user)
        AudioLogFactory(episode=EpisodeFactory(podcast=podcast), user=auth_user)
        AudioLogFactory(user=auth_user)
        BookmarkFactory(user=auth_user)

        response = client.get(reverse("users:stats"))
        assert_ok(response)
        assert response.context["stats"]["subscribed"] == 1
        assert response.context["stats"]["listened"] == 3


class TestImportExportPodcastFeeds:
    def test_get(self, client, auth_user, assert_ok):
        assert_ok(client.get(reverse("users:import_export_podcast_feeds")))


class TestImportPodcastFeeds:
    url = reverse_lazy("users:import_podcast_feeds")

    @pytest.fixture
    def upload_file(self):
        return SimpleUploadedFile(
            "feeds.opml",
            (pathlib.Path(__file__).parent / "mocks" / "feeds.opml").read_bytes(),
            content_type="text/xml",
        )

    def test_post_has_new_feeds(self, client, auth_user, upload_file, assert_ok):
        podcast = PodcastFactory(
            rss="https://feeds.99percentinvisible.org/99percentinvisible"
        )

        assert_ok(
            client.post(
                self.url,
                data={"opml": upload_file},
                HTTP_HX_TARGET="opml-import-form",
            )
        )

        assert Subscription.objects.filter(user=auth_user, podcast=podcast).exists()

    def test_post_has_no_new_feeds(
        self, client, auth_user, mocker, upload_file, assert_ok
    ):
        SubscriptionFactory(
            podcast__rss="https://feeds.99percentinvisible.org/99percentinvisible",
            user=auth_user,
        )

        assert_ok(
            client.post(
                self.url,
                data={"opml": upload_file},
                HTTP_HX_TARGET="opml-import-form",
            )
        )

        assert Subscription.objects.filter(user=auth_user).exists()

    def test_post_is_empty(self, client, auth_user, mocker, upload_file, assert_ok):

        assert_ok(
            client.post(
                self.url,
                data={"opml": upload_file},
                HTTP_HX_TARGET="opml-import-form",
            )
        )

        assert not Subscription.objects.filter(user=auth_user).exists()


class TestExportPodcastFeeds:

    url = reverse_lazy("users:export_podcast_feeds")

    def test_export_opml(self, client, subscription, assert_ok):
        response = client.post(self.url)
        assert_ok(response)
        assert response["Content-Type"] == "text/x-opml"


class TestDeleteAccount:
    url = reverse_lazy("users:delete_account")

    def test_get(self, client, auth_user, assert_ok):
        # make sure we don't accidentally delete account on get request
        response = client.get(self.url)
        assert_ok(response)
        assert User.objects.exists()

    def test_post_unconfirmed(self, client, auth_user, assert_ok):
        response = client.post(self.url)
        assert_ok(response)
        assert User.objects.exists()

    def test_post_confirmed(self, client, auth_user):
        response = client.post(self.url, {"confirm-delete": True})
        assert response.url == settings.HOME_URL
        assert not User.objects.exists()


class TestSocialAccountTemplates:
    """Test overridden allauth account templates."""

    @pytest.fixture
    def req(self, rf):
        return rf.get("/")

    def test_signup(self, req):
        assert get_template("socialaccount/signup.html").render({}, request=req)

    def test_login(self, req):
        assert get_template("socialaccount/login.html").render({}, request=req)


class TestAccountTemplates:
    """Test overridden allauth account templates."""

    @pytest.fixture
    def req(self, rf):
        return rf.get("/")

    @pytest.fixture
    def auth_req(self, req, user, mocker):
        req.user = user

        req.player = mocker.Mock()
        req.player.get.return_value = None

        return req

    def test_email_verification_required(self, req):
        assert get_template("account/verified_email_required.html").render(
            {}, request=req
        )

    def test_verification_sent(self, req):
        assert get_template("account/verification_sent.html").render({}, request=req)

    def test_email(self, auth_req):
        EmailAddressFactory(user=auth_req.user)
        assert get_template("account/email.html").render(
            {"user": auth_req.user}, request=auth_req
        )

    def test_email_confirm(self, req, mocker):
        confirmation = mocker.Mock()
        confirmation.key = "test"
        assert get_template("account/email_confirm.html").render(
            {
                "confirmation": confirmation,
            },
            request=req,
        )

    def test_email_confirm_no_confirmation(self, req):
        assert get_template("account/email_confirm.html").render(
            {
                "confirmation": None,
            },
            request=req,
        )

    def test_account_inactive(self, req):
        assert get_template("account/account_inactive.html").render({}, request=req)

    def test_password_change(self, req):
        assert get_template("account/password_change.html").render({}, request=req)

    def test_password_reset(self, req):
        assert get_template("account/password_reset.html").render({}, request=req)

    def test_password_reset_done(self, req):
        assert get_template("account/password_reset_done.html").render({}, request=req)

    def test_password_reset_from_key_done(self, req):
        assert get_template("account/password_reset_from_key_done.html").render(
            {}, request=req
        )

    def test_password_set(self, req):
        assert get_template("account/password_set.html").render({}, request=req)

    def test_login(self, req):
        assert get_template("account/login.html").render({}, request=req)

    def test_signup(self, req):
        assert get_template("account/signup.html").render({}, request=req)
