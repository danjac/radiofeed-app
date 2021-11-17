from datetime import timedelta

from jcasts.podcasts.podcastindex import fetch_recent_feeds


class TestFetchRecentFeeds:
    def test_fetch(self, mocker, podcast, mock_parse_podcast_feed):
        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "feeds": [
                        {"url": podcast.rss},
                        {"url": "https://another-url.rss"},
                    ]
                }

        mock_get = mocker.patch("requests.get", return_value=MockResponse())
        assert fetch_recent_feeds(timedelta(hours=1), limit=100) == 1

        mock_get.assert_called()
        mock_parse_podcast_feed.assert_called_with(podcast.id)

        podcast.refresh_from_db()
        assert podcast.podcastindex
        assert podcast.queued
