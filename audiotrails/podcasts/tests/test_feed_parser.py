from __future__ import annotations

import http
import pathlib

from unittest import mock

import requests

from django.test import TestCase

from audiotrails.podcasts.date_parser import parse_date
from audiotrails.podcasts.factories import CategoryFactory, PodcastFactory
from audiotrails.podcasts.feed_parser import get_categories_dict, parse_feed


class MockResponse:
    def __init__(
        self,
        url: str,
        status: int = http.HTTPStatus.OK,
        content: bytes = b"",
        headers: None | dict = None,
    ):
        self.url = url
        self.content = content
        self.headers = headers or {}
        self.status_code = status

    def raise_for_status(self) -> None:
        ...


class BadMockResponse(MockResponse):
    def raise_for_status(self) -> None:
        raise requests.RequestException()


class FeedParserTests(TestCase):

    mock_file = "rss_mock.xml"
    mock_http_get = "requests.get"
    rss = "https://mysteriousuniverse.org/feed/podcast/"
    updated = "Wed, 01 Jul 2020 15:25:26 +0000"

    @classmethod
    def setUpTestData(cls) -> None:

        [
            CategoryFactory(name=name)
            for name in (
                "Philosophy",
                "Science",
                "Social Sciences",
                "Society & Culture",
                "Spirituality",
                "Religion & Spirituality",
            )
        ]

        cls.podcast = PodcastFactory(cover_url=None, pub_date=None)

    def setUp(self):
        self.content = open(
            pathlib.Path(__file__).parent / "mocks" / self.mock_file, "rb"
        ).read()

    def get_feedparser_content(self, *args, **kwargs) -> bytes:
        return open(
            pathlib.Path(__file__).parent / "mocks" / self.mock_file, "rb"
        ).read()

    def tearDown(self) -> None:
        get_categories_dict.cache_clear()

    def test_parse_feed(self):

        with mock.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=self.podcast.rss,
                content=self.get_feedparser_content(),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        ):
            episodes = parse_feed(self.podcast)

        self.assertEqual(len(episodes), 20)

        self.podcast.refresh_from_db()

        self.assertEqual(self.podcast.title, "Mysterious Universe")
        self.assertTrue(self.podcast.rss)

        self.assertEqual(
            self.podcast.description,
            "Always interesting and often hilarious, join hosts Aaron Wright and Benjamin Grundy as they investigate the latest in futurology, weird science, consciousness research, alternative history, cryptozoology, UFOs, and new-age absurdity.",
        )
        self.assertEqual(self.podcast.creators, "8th Kind")

        self.assertTrue(self.podcast.modified)
        self.assertEqual(self.podcast.modified.day, 1)
        self.assertEqual(self.podcast.modified.month, 7)
        self.assertEqual(self.podcast.modified.year, 2020)

        self.assertTrue(self.podcast.etag)
        self.assertTrue(self.podcast.explicit)
        self.assertTrue(self.podcast.cover_url)

        categories = [c.name for c in self.podcast.categories.all()]

        self.assertEqual(
            self.podcast.pub_date, parse_date("Fri, 19 Jun 2020 16:58:03 +0000")
        )

        self.assertIn("Science", categories)
        self.assertIn("Religion & Spirituality", categories)
        self.assertIn("Society & Culture", categories)
        self.assertIn("Philosophy", categories)

        self.assertTrue(self.podcast.modified)

    def test_parse_feed_permanent_redirect(self):
        with mock.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url="https://example.com/test.xml",
                status=http.HTTPStatus.PERMANENT_REDIRECT,
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
                content=self.get_feedparser_content(),
            ),
        ):
            episodes = parse_feed(self.podcast)

        self.assertEqual(len(episodes), 20)

        self.podcast.refresh_from_db()

        self.assertEqual(self.podcast.rss, "https://example.com/test.xml")
        self.assertTrue(self.podcast.modified)

    def test_parse_feed_not_modified(self):
        with mock.patch(
            self.mock_http_get,
            return_value=MockResponse(
                self.podcast.rss, status=http.HTTPStatus.NOT_MODIFIED
            ),
        ):
            episodes = parse_feed(self.podcast)

        self.assertEqual(episodes, [])

        self.podcast.refresh_from_db()
        self.assertTrue(self.podcast.active)
        self.assertFalse(self.podcast.modified)

    def test_parse_feed_gone(self):
        with mock.patch(
            self.mock_http_get, return_value=BadMockResponse(self.podcast.rss)
        ):
            episodes = parse_feed(self.podcast)

        self.assertEqual(episodes, [])

        self.podcast.refresh_from_db()
        self.assertFalse(self.podcast.active)
        self.assertTrue(self.podcast.exception)
