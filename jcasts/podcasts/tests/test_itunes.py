import pytest
import requests

from django.core.cache import cache

from jcasts.podcasts import itunes
from jcasts.podcasts.factories import PodcastFactory
from jcasts.podcasts.models import Podcast

MOCK_RESULT = {
    "feedUrl": "https://feeds.fireside.fm/testandcode/rss",
    "collectionName": "Test & Code : Python Testing",
    "artworkUrl600": "https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
}


def patch_request(mocker, response):
    return mocker.patch("requests.get", return_value=response, autospec=True)


@pytest.fixture
def mock_good_response(mocker):
    class MockResponse:
        def raise_for_status(self):
            ...

        def json(self):
            return {
                "results": [MOCK_RESULT],
            }

    yield patch_request(mocker, MockResponse())


@pytest.fixture
def mock_bad_response(mocker):
    class MockResponse:
        def raise_for_status(self):
            raise requests.HTTPError()

    yield patch_request(mocker, MockResponse())


@pytest.fixture
def mock_invalid_response(mocker):
    class MockResponse:
        def raise_for_status(self):
            ...

        def json(self):
            return {"results": [{"id": 12345, "url": "bad-url"}]}

    yield patch_request(mocker, MockResponse())


class TestTopRated:
    def test_new(self, db, mocker):
        mocker.patch(
            "jcasts.podcasts.itunes.fetch_top_rated",
            return_value={"feed": {"results": [{"id": "12345"}]}},
        )
        mocker.patch(
            "jcasts.podcasts.itunes.fetch_lookup",
            return_value={"results": [MOCK_RESULT]},
        )

        feeds = itunes.top_rated()
        assert len(feeds) == 1
        podcasts = Podcast.objects.filter(promoted=True)
        assert podcasts.count() == 1
        assert podcasts.first().title == "Test & Code : Python Testing"

    def test_exception(self, db, mocker):
        mocker.patch(
            "jcasts.podcasts.itunes.fetch_top_rated",
            side_effect=requests.HTTPError,
        )
        feeds = itunes.top_rated()
        assert len(feeds) == 0

    def test_existing(self, db, mocker):
        mocker.patch(
            "jcasts.podcasts.itunes.fetch_top_rated",
            return_value={"feed": {"results": [{"id": "12345"}]}},
        )
        mocker.patch(
            "jcasts.podcasts.itunes.fetch_lookup",
            return_value={"results": [MOCK_RESULT]},
        )

        podcast = PodcastFactory(rss=MOCK_RESULT["feedUrl"])

        feeds = itunes.top_rated()
        assert len(feeds) == 1
        assert feeds[0].podcast == podcast

        podcast.refresh_from_db()
        assert podcast.promoted


class TestSearch:
    cache_key = "itunes:6447567a64413d3d"

    def test_not_ok(self, db, mock_bad_response):
        assert itunes.search("test") == []
        assert not Podcast.objects.exists()

    def test_ok(self, db, mock_good_response):
        feeds = itunes.search("test")
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].url).exists()

    def test_bad_data(self, db, mock_invalid_response):
        feeds = itunes.search("test")
        assert len(feeds) == 0

    def test_is_not_cached(
        self,
        db,
        mock_good_response,
        locmem_cache,
    ):

        feeds = itunes.search_cached("test")

        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].url).exists()

        assert cache.get(self.cache_key) == feeds

    def test_is_cached(
        self,
        db,
        mock_good_response,
        locmem_cache,
    ):

        cache.set(
            self.cache_key,
            [itunes.Feed(url="https://example.com", title="test")],
        )

        feeds = itunes.search_cached("test")

        assert len(feeds) == 1
        assert not Podcast.objects.filter(rss=feeds[0].url).exists()

        mock_good_response.assert_not_called()

    def test_podcast_exists(self, db, mock_good_response):
        PodcastFactory(rss="https://feeds.fireside.fm/testandcode/rss")
        feeds = itunes.search("test")
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].url).exists()
