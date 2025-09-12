import pathlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertTemplateUsed

from radiofeed.episodes.middleware import PlayerDetails
from radiofeed.episodes.tests.factories import AudioLogFactory, BookmarkFactory
from radiofeed.podcasts.models import Subscription
from radiofeed.podcasts.tests.factories import PodcastFactory, SubscriptionFactory
from radiofeed.tests.asserts import assert200
from radiofeed.users.emails import get_unsubscribe_signer
from radiofeed.users.models import User
from radiofeed.users.tests.factories import EmailAddressFactory


class MockGoogleAdapter:
    def list_providers(self, request):
        return ["Google"]


class Test3rdPartyAuthTemplates:
    """Test customized 3rd party authentication templates"""

    @pytest.mark.parametrize(
        "template",
        [
            "account/email.html",
            "account/email_confirm.html",
            "account/login.html",
            "account/password_change.html",
            "account/password_reset.html",
            "account/password_reset_done.html",
            "account/password_reset_from_key.html",
            "account/password_set.html",
            "account/signup.html",
            "socialaccount/connections.html",
            "socialaccount/login.html",
            "socialaccount/signup.html",
        ],
    )
    @pytest.mark.django_db
    def test_template(self, rf, mocker, user, template):
        req = rf.get("/")
        req.user = user
        req.session = {}
        req.player = PlayerDetails(request=req)

        mocker.patch(
            "radiofeed.users.templatetags.users.get_adapter",
            return_value=MockGoogleAdapter(),
        )
        response = TemplateResponse(req, template)
        response.render()
        assert response.template_name == template


class TestUserPreferences:
    url = reverse_lazy("users:preferences")

    @pytest.mark.django_db
    def test_get(self, client, auth_user):
        response = client.get(self.url, headers={"HX-Request": "true"})
        assert200(response)
        assertTemplateUsed(response, "account/preferences.html")

    @pytest.mark.django_db
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

    @pytest.mark.django_db
    def test_post_not_htmx(self, client, auth_user):
        response = client.post(
            self.url,
            {
                "send_email_notifications": False,
            },
        )
        assert response.url == self.url

        auth_user.refresh_from_db()

        assert not auth_user.send_email_notifications


class TestUserStats:
    url = reverse_lazy("users:stats")
    template = "account/stats.html"

    @pytest.mark.django_db
    def test_stats(self, client, auth_user):
        SubscriptionFactory(subscriber=auth_user)
        AudioLogFactory(user=auth_user)
        BookmarkFactory(user=auth_user)

        response = client.get(self.url)

        assert200(response)

        assertTemplateUsed(response, self.template)

    @pytest.mark.django_db
    def test_stats_plural(self, client, auth_user):
        AudioLogFactory.create_batch(3, user=auth_user)
        BookmarkFactory.create_batch(3, user=auth_user)
        SubscriptionFactory.create_batch(3, subscriber=auth_user)

        response = client.get(self.url)

        assert200(response)

        assertTemplateUsed(response, self.template)


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

    @pytest.mark.django_db
    def test_get(self, client, auth_user):
        response = client.get(self.url)
        assertTemplateUsed(response, "account/podcast_feeds.html")
        assert200(response)

    @pytest.mark.django_db
    def test_post_has_new_feeds(self, client, auth_user, upload_file):
        podcast = PodcastFactory(
            rss="https://feeds.99percentinvisible.org/99percentinvisible"
        )

        response = client.post(
            self.url,
            data={"opml": upload_file},
        )
        assert response.url == self.url
        assert Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()

    @pytest.mark.django_db
    def test_post_invalid_form(self, client, auth_user):
        response = client.post(
            self.url,
            data={"opml": "test.xml"},
            headers={
                "HX-Request": "true",
                "HX-Target": "import-feeds-form",
            },
        )

        assert200(response)
        assert not Subscription.objects.filter(subscriber=auth_user).exists()

    @pytest.mark.django_db
    def test_post_podcast_not_in_db(self, client, auth_user, upload_file):
        response = client.post(
            self.url,
            data={"opml": upload_file},
            headers={
                "HX-Request": "true",
                "HX-Target": "import-feeds-form",
            },
        )
        assert200(response)

        assert Subscription.objects.filter(subscriber=auth_user).count() == 0

    @pytest.mark.django_db
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
            headers={
                "HX-Request": "true",
                "HX-Target": "import-feeds-form",
            },
        )

        assert200(response)
        assert Subscription.objects.filter(subscriber=auth_user).exists()

    @pytest.mark.django_db
    def test_post_is_empty(self, client, auth_user, upload_file):
        response = client.post(
            self.url,
            data={"opml": upload_file},
            headers={
                "HX-Request": "true",
                "HX-Target": "import-feeds-form",
            },
        )
        assert200(response)
        assert not Subscription.objects.filter(subscriber=auth_user).exists()


class TestExportPodcastFeeds:
    url = reverse_lazy("users:export_podcast_feeds")

    @pytest.mark.django_db
    def test_export_opml(self, client, subscription):
        response = client.get(self.url)
        assert response["Content-Type"] == "text/x-opml"


class TestDeleteAccount:
    url = reverse_lazy("users:delete_account")

    @pytest.mark.django_db
    def test_get_not_logged_in(self, client):
        response = client.get(self.url)
        assert200(response)
        assertTemplateUsed(response, "account/delete_account.html")

    @pytest.mark.django_db
    def test_post_not_logged_in(self, client):
        response = client.post(self.url, {"confirm-delete": True})
        assert200(response)

    @pytest.mark.django_db
    def test_get(self, client, auth_user):
        # make sure we don't accidentally delete account on get request
        response = client.get(self.url)
        assert200(response)
        assertTemplateUsed(response, "account/delete_account.html")
        assert User.objects.exists()

    @pytest.mark.django_db
    def test_post_unconfirmed(self, client, auth_user):
        response = client.get(self.url)
        assert200(response)
        assert User.objects.exists()

    @pytest.mark.django_db
    def test_post_confirmed(self, client, auth_user):
        response = client.post(self.url, {"confirm-delete": True})
        assert response.url == reverse("index")
        assert not User.objects.exists()


class TestUnsubscribe:
    @pytest.fixture
    def email_address(self):
        return EmailAddressFactory()

    @pytest.mark.django_db
    def test_no_email(self, client):
        response = client.get(reverse("users:unsubscribe"))
        assert response.url == reverse("index")

    @pytest.mark.django_db
    def test_email_does_not_exist(self, client):
        response = client.get(
            reverse("users:unsubscribe"),
            {
                "email": get_unsubscribe_signer().sign("rando@gmail.com"),
            },
        )
        assert response.url == reverse("index")

    @pytest.mark.django_db
    def test_bad_signature(self, client, email_address):
        response = client.get(
            reverse("users:unsubscribe"),
            {"email": email_address.email},
        )
        assert response.url == reverse("index")
        email_address.refresh_from_db()
        assert email_address.user.send_email_notifications is True

    @pytest.mark.django_db
    def test_ok_not_logged_in(self, client, email_address):
        response = client.get(
            reverse("users:unsubscribe"),
            {
                "email": get_unsubscribe_signer().sign(email_address.email),
            },
        )
        assert response.url == reverse("index")
        email_address.refresh_from_db()
        assert email_address.user.send_email_notifications is False

    @pytest.mark.django_db
    def test_ok_is_logged_in(self, client, auth_user):
        email_address = EmailAddressFactory(user=auth_user)
        response = client.get(
            reverse("users:unsubscribe"),
            {
                "email": get_unsubscribe_signer().sign(email_address.email),
            },
        )
        assert response.url == reverse("index")
        email_address.refresh_from_db()
        assert email_address.user.send_email_notifications is False
