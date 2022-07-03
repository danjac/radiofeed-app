import pathlib

import pytest
import requests

from django.core.cache import cache

from radiofeed.podcasts import itunes
from radiofeed.podcasts.factories import PodcastFactory
from radiofeed.podcasts.models import Podcast

MOCK_RESULT = {
    "feedUrl": "https://feeds.fireside.fm/testandcode/rss",
    "collectionName": "Test & Code : Python Testing",
    "collectionViewUrl": "https//itunes.com/id123345",
    "artworkUrl600": "https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
}


class MockResponse:
    def __init__(self, *, mock_file=None, json=None, exception=None):
        if mock_file is not None:
            self.content = (
                pathlib.Path(__file__).parent / "mocks" / mock_file
            ).read_bytes()
        else:
            self.content = b""

        self.json_data = json
        self.exception = exception

    def raise_for_status(self):
        if self.exception:
            raise self.exception

    def json(self):
        return self.json_data


def mock_request(mocker, response):
    return mocker.patch("requests.get", return_value=response, autospec=True)


@pytest.fixture
def mock_good_response(mocker):
    yield mock_request(mocker, MockResponse(json={"results": [MOCK_RESULT]}))


@pytest.fixture
def mock_bad_response(mocker):
    yield mock_request(mocker, MockResponse(exception=requests.HTTPError()))


@pytest.fixture
def mock_invalid_response(mocker):
    yield mock_request(
        mocker, MockResponse(json={"results": [{"id": 12345, "url": "bad-url"}]})
    )


class TestCrawl:
    def test_crawl(self, db, mocker):
        def side_effect(*args, **kwargs):

            url = args[0]

            if url == "https://itunes.apple.com/lookup":
                return MockResponse(json={"results": [MOCK_RESULT]})

            if url.endswith("/genre/podcasts/id26"):
                return MockResponse(mock_file="podcasts.html")

            if "/genre/podcasts" in url:
                return MockResponse(mock_file="genre.html")

            return MockResponse()

        mocker.patch("requests.get", side_effect=side_effect)

        list(itunes.crawl(["us"]))

        assert Podcast.objects.count() == 1


class TestSearch:
    cache_key = "itunes:6447567a64413d3d"

    def test_not_ok(self, db, mock_bad_response):
        with pytest.raises(requests.HTTPError):
            list(itunes.search("test"))
        assert not Podcast.objects.exists()

    def test_ok(self, db, mock_good_response):
        feeds = list(itunes.search("test"))
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss).exists()

    def test_bad_data(self, db, mock_invalid_response):
        feeds = list(itunes.search("test"))
        assert len(feeds) == 0

    def test_is_not_cached(
        self,
        db,
        mock_good_response,
        locmem_cache,
    ):

        feeds = itunes.search_cached("test")

        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss).exists()

        assert cache.get(self.cache_key) == feeds

    def test_is_cached(
        self,
        db,
        mock_good_response,
        locmem_cache,
    ):

        cache.set(
            self.cache_key,
            [
                itunes.Feed(
                    rss="https://example.com",
                    title="test",
                    url="https://example.com/id1234",
                )
            ],
        )

        feeds = itunes.search_cached("test")

        assert len(feeds) == 1
        assert not Podcast.objects.filter(rss=feeds[0].url).exists()

        mock_good_response.assert_not_called()

    def test_podcast_exists(self, db, mock_good_response):
        PodcastFactory(rss="https://feeds.fireside.fm/testandcode/rss")
        feeds = list(itunes.search("test"))
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss).exists()
