import pathlib

import pytest
import requests
from django.core.cache import cache

from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import create_podcast

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


@pytest.fixture()
def mock_good_response(mocker):
    return mocker.patch(
        "requests.get",
        return_value=MockResponse(
            json={
                "results": [MOCK_RESULT],
            },
        ),
    )


@pytest.fixture()
def mock_bad_response(mocker):
    return mocker.patch(
        "requests.get",
        return_value=MockResponse(
            exception=requests.RequestException("fail"),
        ),
    )


@pytest.fixture()
def mock_invalid_response(mocker):
    return mocker.patch(
        "requests.get",
        return_value=MockResponse(
            json={
                "results": [
                    {
                        "id": 12345,
                        "url": "bad-url",
                    }
                ]
            }
        ),
    )


class TestCrawl:
    @pytest.mark.django_db()
    def test_crawl(self, mocker):
        def _mock_get(url, *args, **kwargs):
            if url == "https://itunes.apple.com/lookup":
                return MockResponse(json={"results": [MOCK_RESULT]})

            if url.endswith("/genre/podcasts/id26"):
                return MockResponse(mock_file="podcasts.html")

            if "/genre/podcasts" in url:
                return MockResponse(mock_file="genre.html")

            return MockResponse()

        mocker.patch("requests.get", _mock_get)

        list(itunes.crawl())

        assert Podcast.objects.count() == 1

    @pytest.mark.django_db()
    def test_crawl_with_parse_genre_error(self, mocker):
        def _mock_get(url, *args, **kwargs):
            if url == "https://itunes.apple.com/lookup":
                return MockResponse(json={"results": [MOCK_RESULT]})

            if url.endswith("/genre/podcasts/id26"):
                return MockResponse(mock_file="podcasts.html")

            if "/genre/podcasts" in url:
                return MockResponse(exception=requests.RequestException("oops"))

            return MockResponse()

        mocker.patch("requests.get", _mock_get)

        list(itunes.crawl())

        assert Podcast.objects.count() == 0

    @pytest.mark.django_db()
    def test_crawl_with_parse_feeds_error(self, mocker):
        def _mock_get(url, *args, **kwargs):
            if url == "https://itunes.apple.com/lookup":
                return MockResponse(exception=requests.RequestException("oops"))

            if url.endswith("/genre/podcasts/id26"):
                return MockResponse(mock_file="podcasts.html")

            if "/genre/podcasts" in url:
                return MockResponse(mock_file="genre.html")

            return MockResponse()

        mocker.patch("requests.get", _mock_get)

        list(itunes.crawl())

        assert Podcast.objects.count() == 0

    @pytest.mark.django_db()
    def test_crawl_with_podcasts_url_error(self, mocker):
        def _mock_get(url, *args, **kwargs):
            if url == "https://itunes.apple.com/lookup":
                return MockResponse(json={"results": [MOCK_RESULT]})

            if url.endswith("/genre/podcasts/id26"):
                return MockResponse(exception=requests.RequestException("oops"))

            if "/genre/podcasts" in url:
                return MockResponse(mock_file="genre.html")

            return MockResponse()

        mocker.patch("requests.get", _mock_get)

        list(itunes.crawl())

        assert Podcast.objects.count() == 0


class TestSearch:
    @pytest.mark.django_db()
    def test_not_ok(self, mock_bad_response):
        with pytest.raises(requests.RequestException):
            list(itunes.search("test"))
        assert not Podcast.objects.exists()

    @pytest.mark.django_db()
    def test_ok(self, mock_good_response):
        feeds = list(itunes.search("test"))
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss).exists()

    @pytest.mark.django_db()
    def test_bad_data(self, mock_invalid_response):
        feeds = list(itunes.search("test"))
        assert not feeds

    @pytest.mark.django_db()
    @pytest.mark.usefixtures("_locmem_cache")
    def test_is_not_cached(self, mock_good_response):
        feeds = itunes.search("test")

        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss).exists()

        assert cache.get(itunes.search_cache_key("test")) == feeds

    @pytest.mark.django_db()
    @pytest.mark.usefixtures("_locmem_cache")
    def test_is_cached(self, mock_good_response):
        cache.set(
            itunes.search_cache_key("test"),
            [
                itunes.Feed(
                    rss="https://example.com",
                    title="test",
                    url="https://example.com/id1234",
                )
            ],
        )

        feeds = itunes.search("test")

        assert len(feeds) == 1
        assert not Podcast.objects.filter(rss=feeds[0].url).exists()

        mock_good_response.get.assert_not_called()

    @pytest.mark.django_db()
    def test_podcast_exists(self, mock_good_response):
        create_podcast(rss="https://feeds.fireside.fm/testandcode/rss")

        feeds = list(itunes.search("test"))
        assert len(feeds) == 1
        assert Podcast.objects.filter(rss=feeds[0].rss).exists()
