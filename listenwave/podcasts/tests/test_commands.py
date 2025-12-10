import pytest
from django.core.management import call_command

from listenwave.podcasts.itunes import Feed, ItunesError
from listenwave.podcasts.models import Podcast
from listenwave.podcasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)
from listenwave.users.tests.factories import EmailAddressFactory


class TestFetchTopItunes:
    @pytest.fixture
    def category(self):
        return CategoryFactory(itunes_genre_id=1301)

    @pytest.fixture
    def feed(self):
        return Feed(
            artworkUrl100="https://example.com/test.jpg",
            collectionName="example",
            collectionViewUrl="https://example.com/",
            feedUrl="https://example.com/rss/",
        )

    @pytest.mark.django_db
    def test_ok(self, category, mocker, feed):
        mock_fetch_chart = mocker.patch(
            "listenwave.podcasts.itunes.fetch_chart", return_value=[feed]
        )
        mock_fetch_genre = mocker.patch(
            "listenwave.podcasts.itunes.fetch_genre", return_value=[feed]
        )

        call_command("fetch_top_itunes")
        mock_fetch_chart.assert_called()
        mock_fetch_genre.assert_called()

        assert Podcast.objects.count() == 1
        assert Podcast.objects.filter(promoted=True).count() == 1

    @pytest.mark.django_db
    def test_no_chart_feeds(self, category, mocker, feed):
        mock_fetch_chart = mocker.patch(
            "listenwave.podcasts.itunes.fetch_chart", return_value=[]
        )
        mock_fetch_genre = mocker.patch(
            "listenwave.podcasts.itunes.fetch_genre", return_value=[feed]
        )

        call_command("fetch_top_itunes")
        mock_fetch_chart.assert_called()
        mock_fetch_genre.assert_called()

        assert Podcast.objects.count() == 1

    @pytest.mark.django_db
    def test_itunes_error(self, mocker):
        mock_fetch_chart = mocker.patch(
            "listenwave.podcasts.itunes.fetch_chart",
            side_effect=ItunesError("Error fetching iTunes"),
        )
        call_command("fetch_top_itunes")
        mock_fetch_chart.assert_called()


class TestCreateRecommendations:
    @pytest.mark.django_db
    def test_create_recommendations(self, mocker):
        patched = mocker.patch(
            "listenwave.podcasts.recommender.recommend",
            return_value=RecommendationFactory.create_batch(3),
        )
        call_command("create_recommendations")
        patched.assert_called()


class TestSendRecommendations:
    @pytest.fixture
    def recipient(self):
        return EmailAddressFactory(verified=True, primary=True)

    @pytest.mark.django_db(transaction=True)
    def test_ok(self, recipient, mailoutbox):
        podcast = SubscriptionFactory(subscriber=recipient.user).podcast
        RecommendationFactory(podcast=podcast)
        call_command("send_recommendations")
        assert len(mailoutbox) == 1

    @pytest.mark.django_db(transaction=True)
    def test_no_recommendations(self, recipient, mailoutbox):
        PodcastFactory()
        call_command("send_recommendations")
        assert len(mailoutbox) == 0
