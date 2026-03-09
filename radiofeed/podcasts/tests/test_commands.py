import pytest
from django.core.management import call_command

from radiofeed.podcasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
)


@pytest.mark.django_db
class TestSendPodcastRecommendations:
    @pytest.fixture
    def mock_task(self, mocker):
        return mocker.patch("radiofeed.podcasts.tasks.send_podcast_recommendations")

    def test_has_episodes(self, recipient, mock_task):
        call_command("send_podcast_recommendations")
        mock_task.enqueue.assert_called()


@pytest.mark.django_db
class TestParsePodcastFeeds:
    @pytest.fixture
    def mock_task(self, mocker):
        return mocker.patch("radiofeed.podcasts.tasks.parse_podcast_feed")

    def test_ok(self, mock_task):
        PodcastFactory(pub_date=None)
        call_command("parse_podcast_feeds")
        mock_task.enqueue.assert_called()

    def test_not_scheduled(self, mock_task):
        PodcastFactory(active=False)
        call_command("parse_podcast_feeds")
        mock_task.enqueue.assert_not_called()


@pytest.mark.django_db
class TestFetchItunesFeeds:
    @pytest.fixture
    def category(self):
        return CategoryFactory(itunes_genre_id=1301)

    @pytest.fixture
    def mock_task(self, mocker):
        return mocker.patch("radiofeed.podcasts.tasks.fetch_itunes_feeds")

    def test_ok(self, category, mock_task):
        call_command("fetch_itunes_feeds")
        mock_task.enqueue.assert_called()


@pytest.mark.django_db
class TestCreatePodcastRecommendations:
    def test_create_podcast_recommendations(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.recommender.recommend",
            return_value=RecommendationFactory.create_batch(3),
        )
        call_command("create_podcast_recommendations")
        patched.assert_called()
