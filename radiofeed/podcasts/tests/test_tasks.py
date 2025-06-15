import pytest

from radiofeed.podcasts import itunes
from radiofeed.podcasts.tasks import (
    create_recommendations,
    fetch_top_itunes,
    send_recommendations,
    send_recommendations_email,
)
from radiofeed.podcasts.tests.factories import (
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)


class TestFetchTopItunes:
    @pytest.mark.django_db
    def test_ok(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.itunes.fetch_chart",
            return_value=[
                PodcastFactory(),
            ],
        )
        fetch_top_itunes("gb")
        patched.assert_called()

    @pytest.mark.django_db
    def test_error(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.itunes.fetch_chart",
            side_effect=itunes.ItunesError("Error"),
        )
        fetch_top_itunes("gb")
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
        create_recommendations()
        patched.assert_called()


class TestSendRecommendations:
    @pytest.mark.django_db
    def test_has_recommendations(self, mocker, recipient):
        mock_task = mocker.patch("radiofeed.podcasts.tasks.async_task")
        send_recommendations()
        mock_task.assert_called()


class TestSendRecommendationsEmails:
    @pytest.mark.django_db(transaction=True)
    def test_has_recommendations(self, mailoutbox, recipient):
        subscription = SubscriptionFactory(subscriber=recipient.user)
        RecommendationFactory.create_batch(3, podcast=subscription.podcast)
        send_recommendations_email(recipient.id)
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [recipient.email]
        assert recipient.user.recommended_podcasts.count() == 3

    @pytest.mark.django_db(transaction=True)
    def test_has_no_recommendations(self, mailoutbox, recipient):
        send_recommendations_email(recipient.id)
        assert len(mailoutbox) == 0
        assert recipient.user.recommended_podcasts.count() == 0
