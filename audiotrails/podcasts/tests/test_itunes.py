from __future__ import annotations

from unittest import mock

from django.test import TestCase

from audiotrails.podcasts import itunes
from audiotrails.podcasts.factories import PodcastFactory


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
    @mock.patch("requests.get", return_value=MockResponse())
    def test_no_new_podcasts(self, mock):
        PodcastFactory(rss="https://feeds.fireside.fm/testandcode/rss")
        results, podcasts = itunes.search_itunes("testing")
        self.assertEqual(len(results), 1)
        self.assertEqual(len(podcasts), 0)

    @mock.patch("requests.get", return_value=MockResponse())
    def test_add_new_podcasts(self, mock):
        results, new_podcasts = itunes.search_itunes("testing")
        self.assertEqual(len(results), 1)
        self.assertEqual(len(new_podcasts), 1)
        self.assertEqual(new_podcasts[0].title, "Test & Code : Python Testing")
        self.assertEqual(
            new_podcasts[0].rss, "https://feeds.fireside.fm/testandcode/rss"
        )


class FetchItunesGenreTests(TestCase):
    @mock.patch("requests.get", return_value=MockResponse())
    def test_no_new_podcasts(self, mock):
        PodcastFactory(rss="https://feeds.fireside.fm/testandcode/rss")
        results, podcasts = itunes.fetch_itunes_genre(1)
        self.assertEqual(len(results), 1)
        self.assertEqual(len(podcasts), 0)

    @mock.patch("requests.get", return_value=MockResponse())
    def test_add_new_podcasts(self, mock):
        results, new_podcasts = itunes.fetch_itunes_genre(1)
        self.assertEqual(len(results), 1)
        self.assertEqual(len(new_podcasts), 1)
        self.assertEqual(new_podcasts[0].title, "Test & Code : Python Testing")
        self.assertEqual(
            new_podcasts[0].rss, "https://feeds.fireside.fm/testandcode/rss"
        )
