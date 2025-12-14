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


class TestParsePodcastFeeds:
    @pytest.fixture
    def mock_parse(self, mocker):
        return mocker.patch(
            "listenwave.podcasts.management.commands.parse_podcast_feeds.parse_feed"
        )

    @pytest.mark.django_db
    def test_ok(self, mock_parse):
        PodcastFactory(pub_date=None)
        call_command("parse_podcast_feeds")
        mock_parse.assert_called()

    @pytest.mark.django_db
    def test_not_scheduled(self, mock_parse):
        PodcastFactory(active=False)
        call_command("parse_podcast_feeds")
        mock_parse.assert_not_called()


class TestFetchItunesFeeds:
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
        call_command("fetch_itunes_feeds", min_jitter=0, max_jitter=0)
        mock_fetch_chart.assert_called()
        assert Podcast.objects.filter(promoted=True).exists() is True

    @pytest.mark.django_db
    def test_no_chart_feeds(self, category, mocker, feed):
        mock_fetch_chart = mocker.patch(
            "listenwave.podcasts.itunes.fetch_chart", return_value=[]
        )
        call_command("fetch_itunes_feeds", min_jitter=0, max_jitter=0)
        mock_fetch_chart.assert_called()
        assert Podcast.objects.exists() is False

    @pytest.mark.django_db
    def test_itunes_error(self, mocker):
        mock_fetch_chart = mocker.patch(
            "listenwave.podcasts.itunes.fetch_chart",
            side_effect=ItunesError("Error fetching iTunes"),
        )
        call_command("fetch_itunes_feeds", min_jitter=0, max_jitter=0)
        mock_fetch_chart.assert_called()
        assert Podcast.objects.exists() is False


class TestCreatePodcastRecommendations:
    @pytest.mark.django_db
    def test_create_recommendations(self, mocker):
        patched = mocker.patch(
            "listenwave.podcasts.recommender.recommend",
            return_value=RecommendationFactory.create_batch(3),
        )
        call_command("create_podcast_recommendations")
        patched.assert_called()


class TestSendPodcastRecommendations:
    @pytest.fixture
    def recipient(self):
        return EmailAddressFactory(verified=True, primary=True)

    @pytest.mark.django_db(transaction=True)
    def test_ok(self, recipient, mailoutbox):
        podcast = SubscriptionFactory(subscriber=recipient.user).podcast
        RecommendationFactory(podcast=podcast)
        call_command("send_podcast_recommendations")
        assert len(mailoutbox) == 1

    @pytest.mark.django_db(transaction=True)
    def test_no_recommendations(self, recipient, mailoutbox):
        PodcastFactory()
        call_command("send_podcast_recommendations")
        assert len(mailoutbox) == 0
