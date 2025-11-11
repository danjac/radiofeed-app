import pytest
from django.core.management import call_command

from radiofeed.podcasts.itunes import Feed, ItunesError
from radiofeed.podcasts.tests.factories import (
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)
from radiofeed.users.tests.factories import EmailAddressFactory


class TestFetchTopItunes:
    @pytest.fixture
    def feed(self):
        return Feed(
            artworkUrl100="http://example.com/artwork.jpg",
            collectionName="Example Podcast",
            collectionViewUrl="http://example.com/podcast",
            feedUrl="http://example.com/feed",
        )

    @pytest.mark.django_db
    def test_ok(self, mocker, feed):
        patched = mocker.patch(
            "radiofeed.podcasts.itunes.fetch_chart", return_value=[feed]
        )
        call_command("fetch_top_itunes")
        patched.assert_called()

    @pytest.mark.django_db
    def test_error(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.itunes.fetch_chart",
            side_effect=ItunesError("API error"),
        )
        call_command("fetch_top_itunes")
        patched.assert_called()

    @pytest.mark.django_db
    def test_promote(self, mocker, feed):
        promoted = PodcastFactory(promoted=True)
        patched = mocker.patch(
            "radiofeed.podcasts.itunes.fetch_chart", return_value=[feed]
        )
        call_command("fetch_top_itunes", promote="gb")
        patched.assert_called()
        promoted.refresh_from_db()
        assert promoted.promoted is False

    @pytest.mark.django_db
    def test_promote_invalid_country(self, mocker, feed):
        promoted = PodcastFactory(promoted=True)
        patched = mocker.patch(
            "radiofeed.podcasts.itunes.fetch_chart",
            return_value=[feed],
        )
        call_command("fetch_top_itunes", promote="xx")
        patched.assert_not_called()
        promoted.refresh_from_db()
        assert promoted.promoted is True


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


class TestSendRecommendations:
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
        call_command("send_recommendations")
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [recipient.email]
        assert recipient.user.recommended_podcasts.count() == 3

    @pytest.mark.django_db(transaction=True)
    def test_has_no_recommendations(self, mailoutbox, recipient):
        call_command("send_recommendations")
        assert len(mailoutbox) == 0
        assert recipient.user.recommended_podcasts.count() == 0
