import pytest

from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tasks import (
    fetch_itunes_feeds,
    parse_podcast_feed,
)
from radiofeed.podcasts.tests.factories import (
    CategoryFactory,
)


class TestParsePodcastFeed:
    @pytest.mark.django_db
    def test_ok(self, podcast, mocker, _immediate_task_backend):
        mock_parse = mocker.patch(
            "radiofeed.podcasts.tasks.parse_feed",
            return_value=Podcast.FeedStatus.SUCCESS,
        )
        task = parse_podcast_feed.enqueue(podcast_id=podcast.id)
        assert task.return_value == Podcast.FeedStatus.SUCCESS
        mock_parse.assert_called()


class TestFetchItunesFeeds:
    @pytest.fixture
    def feed(self):
        return itunes.Feed(
            feedUrl="https://example.com/feed",
            collectionViewUrl="https://example.com",
            collectionName="Example Podcast",
            artworkUrl100="https://example.com/image.jpg",
        )

    @pytest.fixture
    def category(self):
        return CategoryFactory(itunes_genre_id=123)

    @pytest.fixture
    def mock_fetch(self, mocker, feed):
        return mocker.patch(
            "radiofeed.podcasts.tasks.itunes.fetch_top_feeds",
            return_value=[feed],
        )

    @pytest.mark.django_db
    def test_popular(self, mock_fetch, category, feed, _immediate_task_backend):
        fetch_itunes_feeds.enqueue(country="us")
        mock_fetch.assert_called()

    @pytest.mark.django_db
    def test_genre(self, mock_fetch, category, feed, _immediate_task_backend):
        fetch_itunes_feeds.enqueue(country="us", genre_id=category.itunes_genre_id)
        mock_fetch.assert_called()

    @pytest.mark.django_db
    def test_error(self, mocker, _immediate_task_backend):
        mock_fetch = mocker.patch(
            "radiofeed.podcasts.tasks.itunes.fetch_top_feeds",
            side_effect=itunes.ItunesError("API error"),
        )
        fetch_itunes_feeds.enqueue(country="us")
        mock_fetch.assert_called()
