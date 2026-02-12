import pytest
from django.core.management import call_command

from radiofeed.podcasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
    RecommendationFactory,
)


class TestParsePodcastFeeds:
    @pytest.fixture
    def mock_task(self, mocker):
        return mocker.patch(
            "radiofeed.podcasts.management.commands.podcasts.tasks.parse_podcast_feed"
        )

    @pytest.mark.django_db
    def test_ok(self, mock_task):
        PodcastFactory(pub_date=None)
        call_command("podcasts", "parse-feeds")
        mock_task.enqueue.assert_called()

    @pytest.mark.django_db
    def test_not_scheduled(self, mock_task):
        PodcastFactory(active=False)
        call_command("podcasts", "parse-feeds")
        mock_task.enqueue.assert_not_called()


class TestFetchItunes:
    @pytest.fixture
    def category(self):
        return CategoryFactory(itunes_genre_id=1301)

    @pytest.fixture
    def mock_task(self, mocker):
        return mocker.patch(
            "radiofeed.podcasts.management.commands.podcasts.tasks.fetch_itunes_feeds"
        )

    @pytest.mark.django_db
    def test_ok(self, category, mock_task):
        call_command("podcasts", "fetch-itunes")
        mock_task.enqueue.assert_called()


class TestCreatePodcastRecommendations:
    @pytest.mark.django_db
    def test_create_podcast_recommendations(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.recommender.recommend",
            return_value=RecommendationFactory.create_batch(3),
        )
        call_command("podcasts", "create-recommendations")
        patched.assert_called()
