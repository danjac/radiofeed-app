import pytest

from radiofeed.podcasts import itunes
from radiofeed.podcasts.jobs import (
    create_recommendations,
    fetch_itunes_chart,
    send_recommendations,
)
from radiofeed.podcasts.tests.factories import (
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)
from radiofeed.users.tests.factories import EmailAddressFactory


class TestFetchItunesChart:
    @pytest.mark.django_db
    def test_itunes_chart(self, mocker):
        mock_fetch = mocker.patch(
            "radiofeed.podcasts.itunes.fetch_chart",
            return_value=[
                PodcastFactory(),
            ],
        )
        fetch_itunes_chart()
        mock_fetch.assert_called()

    @pytest.mark.django_db
    def test_error(self, mocker):
        mock_fetch = mocker.patch(
            "radiofeed.podcasts.itunes.fetch_chart",
            side_effect=itunes.ItunesError("Error"),
        )
        fetch_itunes_chart()
        mock_fetch.assert_called()


class TestCreateRecommendations:
    @pytest.mark.django_db
    def test_create_recommendations(self, mocker):
        mock_recommend = mocker.patch(
            "radiofeed.podcasts.recommender.recommend",
        )
        create_recommendations()
        mock_recommend.assert_called()


class TestSendRecommendationsEmails:
    @pytest.fixture
    def recipient(self):
        return EmailAddressFactory(
            verified=True,
            primary=True,
        )

    @pytest.mark.django_db(transaction=True)
    def test_has_recommendations(self, mailoutbox, recipient):
        subscription = SubscriptionFactory(subscriber=recipient.user)
        RecommendationFactory.create_batch(3, podcast=subscription.podcast)
        send_recommendations()
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [recipient.email]
        assert recipient.user.recommended_podcasts.count() == 3

    @pytest.mark.django_db(transaction=True)
    def test_has_no_recommendations(self, mailoutbox, recipient):
        send_recommendations()
        assert len(mailoutbox) == 0
        assert recipient.user.recommended_podcasts.count() == 0

    @pytest.mark.django_db(transaction=True)
    def test_exception_raised(self, mocker, mailoutbox, recipient):
        mocker.patch(
            "radiofeed.podcasts.jobs.send_notification_email",
            side_effect=Exception("Error"),
        )
        subscription = SubscriptionFactory(subscriber=recipient.user)
        RecommendationFactory.create_batch(3, podcast=subscription.podcast)
        send_recommendations()
        assert len(mailoutbox) == 0
        assert recipient.user.recommended_podcasts.count() == 0
