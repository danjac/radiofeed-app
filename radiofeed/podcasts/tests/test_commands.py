import pytest
from django.core.management import call_command

from radiofeed.podcasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)
from radiofeed.users.tests.factories import EmailAddressFactory


class TestParsePodcastFeeds:
    @pytest.fixture
    def mock_task(self, mocker):
        return mocker.patch(
            "radiofeed.podcasts.management.commands.parse_podcast_feeds.parse_podcast_feed"
        )

    @pytest.mark.django_db
    def test_ok(self, mock_task):
        PodcastFactory(pub_date=None)
        call_command("parse_podcast_feeds")
        mock_task.enqueue.assert_called()

    @pytest.mark.django_db
    def test_not_scheduled(self, mock_task):
        PodcastFactory(active=False)
        call_command("parse_podcast_feeds")
        mock_task.enqueue.assert_not_called()


class TestFetchItunesFeeds:
    @pytest.fixture
    def category(self):
        return CategoryFactory(itunes_genre_id=1301)

    @pytest.fixture
    def mock_task(self, mocker):
        return mocker.patch(
            "radiofeed.podcasts.management.commands.fetch_itunes_feeds.fetch_itunes_feeds"
        )

    @pytest.mark.django_db
    def test_ok(self, category, mock_task):
        call_command("fetch_itunes_feeds")
        mock_task.enqueue.assert_called()


class TestCreatePodcastRecommendations:
    @pytest.mark.django_db
    def test_create_podcast_recommendations(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.recommender.recommend",
            return_value=RecommendationFactory.create_batch(3),
        )
        call_command("create_podcast_recommendations")
        patched.assert_called()


class TestSendPodcastRecommendations:
    @pytest.fixture
    def mock_task(self, mocker):
        return mocker.patch(
            "radiofeed.podcasts.management.commands.send_podcast_recommendations.send_podcast_recommendations"
        )

    @pytest.fixture
    def recipient(self):
        return EmailAddressFactory(verified=True, primary=True)

    @pytest.mark.django_db
    def test_ok(self, recipient, mock_task):
        podcast = SubscriptionFactory(subscriber=recipient.user).podcast
        RecommendationFactory(podcast=podcast)
        call_command("send_podcast_recommendations")
        mock_task.enqueue.assert_called()
