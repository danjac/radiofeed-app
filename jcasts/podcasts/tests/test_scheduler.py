import pytest

from jcasts.podcasts.scheduler import sync_podcast_feed


class TestSyncPodcastFeed:
    @pytest.fixture
    def mock_parse_feed(self, mocker):
        return mocker.patch("jcasts.podcasts.scheduler.parse_feed")

    def test_sync_podcast_feed(self, podcast, mock_parse_feed):
        sync_podcast_feed.delay(podcast.rss)
        mock_parse_feed.assert_called()
