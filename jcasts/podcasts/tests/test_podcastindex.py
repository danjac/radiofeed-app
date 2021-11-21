from datetime import timedelta

from jcasts.podcasts.models import Podcast
from jcasts.podcasts.podcastindex import fetch_new_feeds


class TestFetchRecentFeeds:
    def test_fetch(self, mocker, podcast):
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
        assert fetch_new_feeds(timedelta(hours=1), limit=100) == 1

        mock_get.assert_called()

        assert Podcast.objects.count() == 2
        assert Podcast.objects.filter(rss="https://another-url.rss").exists()
