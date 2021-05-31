import pathlib

from unittest import mock

import feedparser

from django.test import TestCase

from audiotrails.podcasts.factories import CategoryFactory, PodcastFactory
from audiotrails.podcasts.feed_parser import get_categories_dict, parse_feed


class FeedParserTests(TestCase):

    mock_file = "rss_mock.xml"
    rss = "https://mysteriousuniverse.org/feed/podcast/"

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

    def get_feedparser_content(self, *args, **kwargs) -> dict:
        content = open(
            pathlib.Path(__file__).parent / "mocks" / self.mock_file, "rb"
        ).read()

        return feedparser.parse(content)

    def tearDown(self) -> None:
        get_categories_dict.cache_clear()

    def test_parse_feed(self, *mocks):

        with mock.patch("feedparser.parse", return_value=self.get_feedparser_content()):
            episodes = parse_feed(self.podcast)

        self.assertEqual(len(episodes), 20)

        self.podcast.refresh_from_db()

        self.assertEqual(self.podcast.title, "Mysterious Universe")
        self.assertEqual(
            self.podcast.description,
            "Always interesting and often hilarious, join hosts Aaron Wright and Benjamin Grundy as they investigate the latest in futurology, weird science, consciousness research, alternative history, cryptozoology, UFOs, and new-age absurdity.",
        )
        self.assertEqual(self.podcast.creators, "8th Kind")

        self.assertTrue(self.podcast.last_updated)
        self.assertTrue(self.podcast.pub_date)
        self.assertTrue(self.podcast.explicit)
        self.assertTrue(self.podcast.cover_url)

        categories = [c.name for c in self.podcast.categories.all()]

        self.assertIn("Science", categories)
        self.assertIn("Religion & Spirituality", categories)
        self.assertIn("Society & Culture", categories)
        self.assertIn("Philosophy", categories)

        self.assertTrue(self.podcast.last_updated)

    def test_parse_feed_permanent_redirect(self, *mocks):
        with mock.patch(
            "feedparser.parse",
            return_value={
                "status": 301,
                "href": "https://example.com/test.xml",
                **self.get_feedparser_content(),
            },
        ):
            episodes = parse_feed(self.podcast)

        self.assertEqual(len(episodes), 20)

        self.podcast.refresh_from_db()
        self.podcast.rss == "https://example.com/test.xml"

    def test_parse_feed_gone(self, *mocks):
        with mock.patch(
            "feedparser.parse",
            return_value={
                "status": 410,
            },
        ):
            episodes = parse_feed(self.podcast)

        self.assertEqual(episodes, [])

        self.podcast.refresh_from_db()
        self.assertFalse(self.podcast.active)
