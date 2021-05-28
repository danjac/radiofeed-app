import pathlib

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

        cls.podcast = PodcastFactory(cover_image=None, pub_date=None)

    def setUp(self):
        self.content = open(
            pathlib.Path(__file__).parent / "mocks" / self.mock_file, "rb"
        ).read()

    def tearDown(self) -> None:
        get_categories_dict.cache_clear()

    def test_parse_feed(self, *mocks):

        episodes = parse_feed(self.podcast, src=self.content)

        self.assertEqual(len(episodes), 20)

        self.podcast.refresh_from_db()

        self.assertTrue(self.podcast.title)
        self.assertTrue(self.podcast.description)
        self.assertTrue(self.podcast.pub_date)
        self.assertTrue(self.podcast.last_updated)
