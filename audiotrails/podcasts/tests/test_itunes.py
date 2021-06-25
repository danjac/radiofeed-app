from __future__ import annotations

from unittest import mock

import requests

from django.test import TestCase

from audiotrails.podcasts import itunes
from audiotrails.podcasts.factories import CategoryFactory, PodcastFactory
from audiotrails.podcasts.models import Podcast

RSS_FEED_URL = "https://feeds.fireside.fm/testandcode/rss"
RSS_FEED_NAME = "Test & Code : Python Testing"

MOCK_ITUNES_RESPONSE = [
    {
        "feedUrl": RSS_FEED_URL,
        "collectionName": RSS_FEED_NAME,
        "trackViewUrl": "https://podcasts.apple.com/us/podcast/test-code-python-testing-for-software-engineering/id1029487211?uo=4",
        "artworkUrl600": "https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
    },
]

MOCK_ITUNES_RESULTS = itunes._make_search_results(MOCK_ITUNES_RESPONSE)


class MockBadHttpResponse:
    def raise_for_status(self):
        raise requests.HTTPError()


class MockResponse:
    def raise_for_status(self):
        ...

    def json(self) -> dict:
        return {"results": MOCK_ITUNES_RESPONSE}


class SearchResultTests(TestCase):
    def test_cleaned_title(self):
        result = itunes.SearchResult(
            title="<b>test</b>",
            rss="",
            image="",
            itunes="",
        )
        self.assertEqual(result.cleaned_title, "test")


class SearchItunesTests(TestCase):
    @mock.patch("requests.get", autospec=True)
    @mock.patch("django.core.cache.cache.get", return_value=MOCK_ITUNES_RESULTS)
    def test_get_from_cache(self, mock_cache_get, mock_requests_get):
        PodcastFactory(rss=RSS_FEED_URL)
        results, podcasts = itunes.search_itunes("testing")
        self.assertEqual(len(results), 1)
        self.assertEqual(len(podcasts), 0)
        mock_cache_get.assert_called_with("itunes:search:testing")
        mock_requests_get.assert_not_called()

    @mock.patch("requests.get", return_value=MockBadHttpResponse(), autospec=True)
    def test_bad_http_response(self, mock):
        self.assertRaises(itunes.Invalid, itunes.search_itunes, "testing")
        self.assertEqual(Podcast.objects.count(), 0)

    @mock.patch("requests.get", side_effect=requests.Timeout, autospec=True)
    def test_timeout(self, mock):
        self.assertRaises(itunes.Timeout, itunes.search_itunes, "testing")
        self.assertEqual(Podcast.objects.count(), 0)

    @mock.patch("requests.get", return_value=MockResponse(), autospec=True)
    def test_no_new_podcasts(self, mock):
        PodcastFactory(rss=RSS_FEED_URL)
        results, podcasts = itunes.search_itunes("testing")
        self.assertEqual(len(results), 1)
        self.assertEqual(len(podcasts), 0)

    @mock.patch("requests.get", return_value=MockResponse(), autospec=True)
    def test_add_new_podcasts(self, mock):
        results, new_podcasts = itunes.search_itunes("testing")
        self.assertEqual(len(results), 1)
        self.assertEqual(len(new_podcasts), 1)
        self.assertEqual(new_podcasts[0].title, RSS_FEED_NAME)
        self.assertEqual(new_podcasts[0].rss, RSS_FEED_URL)


class CrawlItunesTests(TestCase):
    @mock.patch("requests.get", return_value=MockBadHttpResponse(), autospec=True)
    def test_bad_http_response(self, mock):
        CategoryFactory.create_batch(6)
        num_podcasts = itunes.crawl_itunes(limit=100)
        self.assertEqual(num_podcasts, 0)

    @mock.patch("requests.get", return_value=MockResponse(), autospec=True)
    def test_add_new_podcasts(self, mock):
        CategoryFactory.create_batch(6)
        num_podcasts = itunes.crawl_itunes(limit=100)
        self.assertEqual(num_podcasts, 1)


class FetchItunesGenreTests(TestCase):
    @mock.patch("requests.get", autospec=True)
    @mock.patch("django.core.cache.cache.get", return_value=MOCK_ITUNES_RESULTS)
    def test_get_from_cache(self, mock_cache_get, mock_requests_get):
        PodcastFactory(rss=RSS_FEED_URL)
        results, podcasts = itunes.fetch_itunes_genre(1)
        self.assertEqual(len(results), 1)
        self.assertEqual(len(podcasts), 0)
        mock_cache_get.assert_called_with("itunes:genre:1")
        mock_requests_get.assert_not_called()

    @mock.patch("requests.get", return_value=MockResponse(), autospec=True)
    def test_no_new_podcasts(self, mock):
        PodcastFactory(rss=RSS_FEED_URL)
        results, podcasts = itunes.fetch_itunes_genre(1)
        self.assertEqual(len(results), 1)
        self.assertEqual(len(podcasts), 0)

    @mock.patch("requests.get", return_value=MockResponse(), autospec=True)
    def test_add_new_podcasts(self, mock):
        results, new_podcasts = itunes.fetch_itunes_genre(1)
        self.assertEqual(len(results), 1)
        self.assertEqual(len(new_podcasts), 1)
        self.assertEqual(new_podcasts[0].title, RSS_FEED_NAME)
        self.assertEqual(new_podcasts[0].rss, RSS_FEED_URL)
