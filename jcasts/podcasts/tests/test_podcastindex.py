from __future__ import annotations

import pytest
import requests

from django.core.cache import cache

from jcasts.podcasts import podcastindex
from jcasts.podcasts.factories import PodcastFactory
from jcasts.podcasts.models import Podcast

REQUESTS_POST = "requests.post"

FEED_URL = "https://feeds.fireside.fm/testandcode/rss"
TITLE = "Test & Code : Python Testing"
IMAGE = "https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3"

MOCK_RESULTS = {
    "count": 1,
    "feeds": [
        {
            "id": 12345,
            "url": FEED_URL,
            "title": TITLE,
            "image": IMAGE,
        }
    ],
}


class MockBadResponse:
    def raise_for_status(self):
        raise requests.HTTPError()


class MockResponse:
    _mock_results = MOCK_RESULTS

    def raise_for_status(self):
        ...

    def json(self) -> dict:
        return self._mock_results


@pytest.fixture
def mock_parse_feed(mocker):
    return mocker.patch("jcasts.podcasts.podcastindex.parse_feed.delay")


class TestNewFeeds:
    def test_ok(self, db, mocker, mock_parse_feed):
        mocker.patch(REQUESTS_POST, return_value=MockResponse(), autospec=True)

        feeds = podcastindex.new_feeds()
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].url).exists()
        mock_parse_feed.assert_called()


class TestSearch:
    cache_key = "6447567a64413d3d"

    def test_empty_string(self, db, mocker, mock_parse_feed):
        mock_req = mocker.patch(
            REQUESTS_POST, return_value=MockBadResponse(), autospec=True
        )

        podcastindex.search(" ")
        podcastindex.search("")

        mock_req.assert_not_called()

    def test_not_ok(self, db, mocker, mock_parse_feed):

        mocker.patch(REQUESTS_POST, return_value=MockBadResponse(), autospec=True)
        with pytest.raises(requests.HTTPError):
            podcastindex.search("test")

        assert not Podcast.objects.exists()
        mock_parse_feed.assert_not_called()

    def test_ok(self, db, mocker, mock_parse_feed):
        mocker.patch(REQUESTS_POST, return_value=MockResponse(), autospec=True)
        feeds = podcastindex.search("test")
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].url).exists()
        mock_parse_feed.assert_called()

    def _test_bad_data(self, db, mocker, mock_parse_feed):

        results = {**MOCK_RESULTS}
        results["feeds"][0]["url"] = "bad"

        class BadResponse(MockResponse):
            _mock_results = results

        mocker.patch(REQUESTS_POST, return_value=BadResponse(), autospec=True)
        feeds = podcastindex.search("test")
        assert len(feeds) == 0
        mock_parse_feed.assert_not_called()

    def test_is_not_cached(self, db, mocker, mock_parse_feed, locmem_cache):
        mocker.patch(REQUESTS_POST, return_value=MockResponse(), autospec=True)

        feeds = podcastindex.search("test", cached=True)

        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].url).exists()
        mock_parse_feed.assert_called()

        assert cache.get(self.cache_key) == feeds

    def test_is_cached(self, db, mocker, mock_parse_feed, locmem_cache):
        mock_req = mocker.patch(
            REQUESTS_POST, return_value=MockResponse(), autospec=True
        )

        cache.set(
            self.cache_key,
            [podcastindex.Feed(**result) for result in MOCK_RESULTS["feeds"]],
        )

        feeds = podcastindex.search("test", cached=True)

        assert len(feeds) == 1
        assert not Podcast.objects.filter(rss=feeds[0].url).exists()

        mock_req.assert_not_called()
        mock_parse_feed.assert_not_called()

    def test_podcast_exists(self, db, mocker, mock_parse_feed):
        PodcastFactory(rss=FEED_URL)
        mocker.patch(REQUESTS_POST, return_value=MockResponse(), autospec=True)
        feeds = podcastindex.search("test")
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].url).exists()
        mock_parse_feed.assert_not_called()
