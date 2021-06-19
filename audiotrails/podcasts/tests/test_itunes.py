from __future__ import annotations

from unittest import mock

import requests

from django.test import TestCase

from audiotrails.podcasts import itunes
from audiotrails.podcasts.factories import CategoryFactory, PodcastFactory
from audiotrails.podcasts.models import Podcast


class MockBadHttpResponse:
    def raise_for_status(self):
        raise requests.HTTPError()


class MockResponse:
    def raise_for_status(self):
        ...

    def json(self) -> dict:
        return {
            "results": [
                {
                    "feedUrl": "https://feeds.fireside.fm/testandcode/rss",
                    "trackViewUrl": "https://podcasts.apple.com/us/podcast/test-code-python-testing-for-software-engineering/id1029487211?uo=4",
                    "collectionName": "Test & Code : Python Testing",
                    "artworkUrl600": "https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
                }
            ]
        }


class SearchItunesTests(TestCase):
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
        PodcastFactory(rss="https://feeds.fireside.fm/testandcode/rss")
        results, podcasts = itunes.search_itunes("testing")
        self.assertEqual(len(results), 1)
        self.assertEqual(len(podcasts), 0)

    @mock.patch("requests.get", return_value=MockResponse(), autospec=True)
    def test_add_new_podcasts(self, mock):
        results, new_podcasts = itunes.search_itunes("testing")
        self.assertEqual(len(results), 1)
        self.assertEqual(len(new_podcasts), 1)
        self.assertEqual(new_podcasts[0].title, "Test & Code : Python Testing")
        self.assertEqual(
            new_podcasts[0].rss, "https://feeds.fireside.fm/testandcode/rss"
        )


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
    @mock.patch("requests.get", return_value=MockResponse(), autospec=True)
    def test_no_new_podcasts(self, mock):
        PodcastFactory(rss="https://feeds.fireside.fm/testandcode/rss")
        results, podcasts = itunes.fetch_itunes_genre(1)
        self.assertEqual(len(results), 1)
        self.assertEqual(len(podcasts), 0)

    @mock.patch("requests.get", return_value=MockResponse(), autospec=True)
    def test_add_new_podcasts(self, mock):
        results, new_podcasts = itunes.fetch_itunes_genre(1)
        self.assertEqual(len(results), 1)
        self.assertEqual(len(new_podcasts), 1)
        self.assertEqual(new_podcasts[0].title, "Test & Code : Python Testing")
        self.assertEqual(
            new_podcasts[0].rss, "https://feeds.fireside.fm/testandcode/rss"
        )
