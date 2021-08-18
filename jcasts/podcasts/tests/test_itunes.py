from __future__ import annotations

import pytest
import requests

from jcasts.podcasts import itunes
from jcasts.podcasts.factories import CategoryFactory, PodcastFactory
from jcasts.podcasts.models import Podcast

REQUESTS_GET = "requests.get"

RSS_FEED_URL = "https://feeds.fireside.fm/testandcode/rss"
RSS_FEED_NAME = "Test & Code : Python Testing"
ITUNES_URL = "https://podcasts.apple.com/us/podcast/test-code-python-testing-for-software-engineering/id1029487211?uo=4"
ARTWORK_URL = "https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3"

MOCK_ITUNES_RESPONSE = [
    {
        "feedUrl": RSS_FEED_URL,
        "collectionName": RSS_FEED_NAME,
        "trackViewUrl": ITUNES_URL,
        "artworkUrl600": ARTWORK_URL,
    },
]

MOCK_ITUNES_RESULTS = [itunes.parse_result(result) for result in MOCK_ITUNES_RESPONSE]


class MockBadHttpResponse:
    def raise_for_status(self):
        raise requests.HTTPError()


class MockResponse:
    _mock_results = MOCK_ITUNES_RESPONSE

    def raise_for_status(self):
        ...

    def json(self) -> dict:
        return {"results": self._mock_results}


class TestSearchItunes:
    def test_invalid_result(self, db, mocker):
        class _MockResponse(MockResponse):
            _mock_results = [
                *MOCK_ITUNES_RESPONSE,
                {
                    "collectionName": "Invalid",
                    "trackViewUrl": "https://example.com/itunes",
                    "artworkUrl600": ARTWORK_URL,
                },
            ]

        mocker.patch(REQUESTS_GET, autospec=True, return_value=_MockResponse())
        results, podcasts = itunes.search_itunes("testing")
        assert len(results) == 1
        assert len(podcasts) == 1
        assert podcasts[0].rss == RSS_FEED_URL

    def test_get_from_cache(self, db, mocker):
        mock_requests_get = mocker.patch(REQUESTS_GET, autospec=True)
        mock_cache_get = mocker.patch(
            "django.core.cache.cache.get", return_value=MOCK_ITUNES_RESULTS
        )
        PodcastFactory(rss=RSS_FEED_URL)
        results, podcasts = itunes.search_itunes("testing")
        assert len(results) == 1
        assert len(podcasts) == 0
        mock_cache_get.assert_called_with("itunes:search:testing")
        mock_requests_get.assert_not_called()

    def test_bad_http_response(self, db, mocker):
        mocker.patch(REQUESTS_GET, return_value=MockBadHttpResponse(), autospec=True)
        with pytest.raises(itunes.Invalid):
            itunes.search_itunes("testing")
        assert Podcast.objects.count() == 0

    def test_timeout(self, db, mocker):
        mocker.patch(REQUESTS_GET, side_effect=requests.Timeout, autospec=True)
        with pytest.raises(itunes.Timeout):
            itunes.search_itunes("testing")
        assert Podcast.objects.count() == 0

    def test_no_new_podcasts(self, db, mocker):
        mocker.patch(REQUESTS_GET, return_value=MockResponse(), autospec=True)
        PodcastFactory(rss=RSS_FEED_URL)
        results, podcasts = itunes.search_itunes("testing")
        assert len(results) == 1
        assert len(podcasts) == 0

    def test_add_new_podcasts(self, db, mocker):
        mocker.patch(REQUESTS_GET, return_value=MockResponse(), autospec=True)
        results, new_podcasts = itunes.search_itunes("testing")
        assert len(results) == 1
        assert len(new_podcasts) == 1

        assert new_podcasts[0].title == RSS_FEED_NAME
        assert new_podcasts[0].rss == RSS_FEED_URL


class TestCrawlItunes:
    def test_bad_http_response(self, db, mocker):
        mocker.patch(REQUESTS_GET, return_value=MockBadHttpResponse(), autospec=True)
        CategoryFactory.create_batch(6)
        num_podcasts = itunes.crawl_itunes(limit=100)
        assert num_podcasts == 0

    def test_add_new_podcasts(self, db, mocker):
        mocker.patch(REQUESTS_GET, return_value=MockResponse(), autospec=True)
        CategoryFactory.create_batch(6)
        num_podcasts = itunes.crawl_itunes(limit=100)
        assert num_podcasts == 1


class TestFetchItunesGenre:
    def test_get_from_cache(self, db, mocker):
        mock_requests_get = mocker.patch(REQUESTS_GET, autospec=True)
        mock_cache_get = mocker.patch(
            "django.core.cache.cache.get", return_value=MOCK_ITUNES_RESULTS
        )

        PodcastFactory(rss=RSS_FEED_URL)
        results, podcasts = itunes.fetch_itunes_genre(1)
        assert len(results) == 1
        assert len(podcasts) == 0
        mock_cache_get.assert_called_with("itunes:genre:1")
        mock_requests_get.assert_not_called()

    def test_no_new_podcasts(self, db, mocker):
        mocker.patch(REQUESTS_GET, return_value=MockResponse(), autospec=True)
        PodcastFactory(rss=RSS_FEED_URL)
        results, podcasts = itunes.fetch_itunes_genre(1)

        assert len(results) == 1
        assert len(podcasts) == 0

    def test_add_new_podcasts(self, db, mocker):
        mocker.patch(REQUESTS_GET, return_value=MockResponse(), autospec=True)
        results, new_podcasts = itunes.fetch_itunes_genre(1)

        assert len(results) == 1
        assert len(new_podcasts) == 1

        assert new_podcasts[0].title == RSS_FEED_NAME
        assert new_podcasts[0].rss == RSS_FEED_URL


class TestItunesResultModel:
    def test_get_cleaned_title(self):
        result = itunes.ItunesResult(
            collectionName="<b>test</b>",
            feedUrl="https://example.com/rss.xml",
            trackViewUrl="https://apple.com/feed",
            artworkUrl600="https://apple.com/test.jpg",
        )
        assert result.get_cleaned_title() == "test"
