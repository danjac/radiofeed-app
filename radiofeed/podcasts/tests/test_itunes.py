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


class TestCrawl:
    def test_crawl(self, mocker):
        class MockResponse:
            def __init__(self):

                self.content = (
                    pathlib.Path(__file__).parent / "mocks" / "podcasts.html"
                ).read_bytes()

            def raise_for_status(self):
                # will always be OK
                pass

        mocker.patch("requests.get", return_value=MockResponse())
        mock_parse = mocker.patch("radiofeed.podcasts.itunes.parse_genre")

        list(itunes.crawl())

        assert len(mock_parse.mock_calls) == 3


class TestParseGenre:
    url = "https://podcasts.apple.com/us/genre/podcasts-arts/id1301"

    class MockResponse:
        def __init__(self):

            self.content = (
                pathlib.Path(__file__).parent / "mocks" / "genre.html"
            ).read_bytes()

        def raise_for_status(self):
            # will always be OK
            pass

        def json(self):
            return {"results": [MOCK_RESULT]}

    @pytest.fixture
    def mock_response(self, mocker):
        return self.MockResponse()

    def test_parse(self, mocker, db, mock_response):
        mocker.patch("requests.get", return_value=mock_response)
        assert len(list(itunes.parse_genre(self.url))) == 240


class TestParsePodcastId:
    def test_incorrect_url(self):
        assert itunes.parse_podcast_id("https://example.com") is None

    def test_no_lookup_id(self):
        assert (
            itunes.parse_podcast_id(
                "https://podcasts.apple.com/us/podcast/the-human-action-podcast/"
            )
            is None
        )

    def test_has_lookup_id(self):
        assert (
            itunes.parse_podcast_id(
                "https://podcasts.apple.com/us/podcast/the-human-action-podcast/id884207568"
            )
            == "884207568"
        )


class TestParseFeed:
    def test_exists(self, db, mock_good_response):
        feed = itunes.parse_feed("12345")
        assert feed.rss == "https://feeds.fireside.fm/testandcode/rss"
        assert Podcast.objects.filter(rss=feed.rss).exists()

    def test_not_exists(self, db, mocker):
        class MockResponse:
            def raise_for_status(self):
                ...

            def json(self):
                return {"results": [{"id": 12345, "url": "bad-url"}]}

        patch_request(mocker, MockResponse())
        assert itunes.parse_feed("12345") is None


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
