import pytest
from click.exceptions import Exit
from django.core.management import call_command

from radiofeed.podcasts import itunes
from radiofeed.podcasts.tests.factories import PodcastFactory, RecommendationFactory
from radiofeed.users.tests.factories import EmailAddressFactory


class TestFetchItunesChart:
    @pytest.mark.django_db
    def test_itunes_chart(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.itunes.fetch_chart",
            return_value=[
                PodcastFactory(),
            ],
        )
        call_command("fetch_itunes_chart")
        patched.assert_called()

    @pytest.mark.django_db
    def test_error(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.itunes.fetch_chart",
            side_effect=itunes.ItunesError("Error"),
        )
        with pytest.raises(Exit):
            call_command("fetch_itunes_chart")
        patched.assert_called()


class TestCreateRecommendations:
    @pytest.mark.django_db
    def test_create_recommendations(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.recommender.recommend",
            return_value=[
                ("en", RecommendationFactory.create_batch(3)),
            ],
        )
        call_command("create_recommendations")
        patched.assert_called()


class TestSendRecommendationsEmails:
    @pytest.fixture
    def mock_send(self, mocker):
        return mocker.patch("radiofeed.podcasts.emails.send_recommendations_email")

    @pytest.mark.django_db
    def test_send_emails(self, user, mock_send):
        EmailAddressFactory(
            user=user,
            verified=True,
            primary=True,
        )
        self._call_command()
        mock_send.assert_called()

    @pytest.mark.django_db
    def test_email_not_verified(self, user, mock_send):
        EmailAddressFactory(
            user=user,
            verified=False,
            primary=True,
        )
        self._call_command()
        mock_send.assert_not_called()

    @pytest.mark.django_db
    def test_email_not_primary(self, user, mock_send):
        EmailAddressFactory(
            user=user,
            verified=True,
            primary=False,
        )
        self._call_command()
        mock_send.assert_not_called()

    @pytest.mark.django_db
    def test_user_inactive(self, mock_send):
        EmailAddressFactory(
            user__is_active=False,
            verified=True,
            primary=True,
        )
        self._call_command()
        mock_send.assert_not_called()

    @pytest.mark.django_db
    def test_user_disabled_emails(self, mock_send):
        EmailAddressFactory(
            user__send_email_notifications=False,
            verified=True,
            primary=True,
        )
        self._call_command()
        mock_send.assert_not_called()

    def _call_command(self):
        call_command("send_recommendations")
