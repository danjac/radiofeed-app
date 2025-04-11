import pytest

from radiofeed.podcasts.jobs import (
    create_recommendations,
    fetch_itunes_chart,
    recommend,
    send_recommendations,
    send_recommendations_email,
)
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
        fetch_itunes_chart(country="gb")
        patched.assert_called()

    @pytest.mark.django_db
    def test_empty(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.itunes.fetch_chart",
            return_value=[],
        )
        fetch_itunes_chart(country="gb")
        patched.assert_called()


class TestCreateRecommendations:
    @pytest.mark.django_db
    def test_create_recommendation(self, mocker):
        mock_create = mocker.patch("radiofeed.podcasts.jobs.recommend.delay")
        create_recommendations()
        mock_create.assert_called()


class TestRecommend:
    @pytest.mark.django_db
    def test_create_recommendation(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.recommender.recommend",
            return_value=[
                ("en", RecommendationFactory.create_batch(3)),
            ],
        )
        recommend("en")
        patched.assert_called()


class TestSendRecommendations:
    @pytest.fixture
    def mock_send(self, mocker):
        return mocker.patch("radiofeed.podcasts.jobs.send_recommendations_email.delay")

    @pytest.mark.django_db
    def test_send_emails(self, user, mock_send):
        EmailAddressFactory(
            user=user,
            verified=True,
            primary=True,
        )
        send_recommendations()
        mock_send.assert_called()

    @pytest.mark.django_db
    def test_send_specific_emails(self, user, mock_send):
        EmailAddressFactory(
            user=user,
            verified=True,
            primary=True,
        )
        send_recommendations(addresses=[user.email])
        mock_send.assert_called()

    @pytest.mark.django_db
    def test_email_not_verified(self, user, mock_send):
        EmailAddressFactory(
            user=user,
            verified=False,
            primary=True,
        )
        send_recommendations()
        mock_send.assert_not_called()

    @pytest.mark.django_db
    def test_email_not_primary(self, user, mock_send):
        EmailAddressFactory(
            user=user,
            verified=True,
            primary=False,
        )
        send_recommendations()
        mock_send.assert_not_called()

    @pytest.mark.django_db
    def test_user_inactive(self, mock_send):
        EmailAddressFactory(
            user__is_active=False,
            verified=True,
            primary=True,
        )
        send_recommendations()
        mock_send.assert_not_called()

    @pytest.mark.django_db
    def test_user_disabled_emails(self, mock_send):
        EmailAddressFactory(
            user__send_email_notifications=False,
            verified=True,
            primary=True,
        )
        send_recommendations()
        mock_send.assert_not_called()


class TestSendRecommendationsEmail:
    @pytest.fixture
    def mock_send(self, mocker):
        return mocker.patch("radiofeed.podcasts.emails.send_recommendations_email")

    @pytest.mark.django_db
    def test_send_email(self, user, mock_send):
        recipient = EmailAddressFactory(
            user=user,
            verified=True,
            primary=True,
        )
        send_recommendations_email(recipient.pk)
        mock_send.assert_called()
