import datetime
import json
import pathlib
import uuid

from unittest.mock import Mock, patch

import pytz
import requests

from django.core.validators import ValidationError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from audiotrails.episodes.factories import EpisodeFactory
from audiotrails.episodes.models import Episode
from audiotrails.podcasts.factories import CategoryFactory, PodcastFactory
from audiotrails.podcasts.models import get_categories_dict
from audiotrails.podcasts.rss_parser.date_parser import parse_date
from audiotrails.podcasts.rss_parser.exceptions import HeadersNotFoundError
from audiotrails.podcasts.rss_parser.structures import Audio, Feed, Item


class BaseMockResponse:
    def __init__(self, raises: bool = False):
        self.raises = raises

    def raise_for_status(self) -> None:
        if self.raises:
            raise requests.exceptions.HTTPError()


class MockHeaderResponse(BaseMockResponse):
    def __init__(self):
        super().__init__()
        self.headers = {
            "ETag": uuid.uuid4().hex,
            "Last-Modified": "Sun, 05 Jul 2020 19:21:33 GMT",
        }


class MockResponse(BaseMockResponse):
    def __init__(self, mock_file: str = None, raises: bool = False):
        super().__init__(raises)
        self.headers = {
            "ETag": uuid.uuid4().hex,
            "Last-Modified": "Sun, 05 Jul 2020 19:21:33 GMT",
        }

        if mock_file:
            self.content = open(
                pathlib.Path(__file__).parent / "mocks" / mock_file, "rb"
            ).read()
        self.raises = raises

    def json(self) -> str:
        return json.loads(self.content)


class ParseRssTests(TestCase):

    rss = "https://mysteriousuniverse.org/feed/podcast/"

    def tearDown(self) -> None:
        get_categories_dict.cache_clear()

    @patch("requests.head", autospec=True, side_effect=requests.RequestException)
    def test_parse_error(self, *mocks: Mock) -> None:
        podcast = PodcastFactory()
        self.assertRaises(HeadersNotFoundError, podcast.sync_rss_feed)
        podcast.refresh_from_db()
        self.assertEqual(podcast.num_retries, 1)

    @patch("requests.head", autospec=True, return_value=MockHeaderResponse())
    @patch("requests.get", autospec=True, return_value=MockResponse("rss_mock.xml"))
    def test_parse(self, *mocks: Mock) -> None:
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
        podcast = PodcastFactory(
            rss=self.rss,
            last_updated=None,
            pub_date=None,
        )
        self.assertTrue(podcast.sync_rss_feed())
        podcast.refresh_from_db()

        self.assertTrue(podcast.last_updated)
        self.assertTrue(podcast.pub_date)

        self.assertTrue(podcast.etag)
        self.assertTrue(podcast.cover_image)
        self.assertTrue(podcast.extracted_text)

        self.assertEqual(podcast.title, "Mysterious Universe")
        self.assertEqual(podcast.creators, "8th Kind")
        self.assertEqual(podcast.categories.count(), 6)
        self.assertEqual(podcast.episode_set.count(), 20)

    @patch("requests.head", autospec=True, return_value=MockHeaderResponse())
    @patch("requests.get", autospec=True, return_value=MockResponse("rss_mock.xml"))
    def test_parse_if_already_updated(self, *mocks: Mock) -> None:
        podcast = PodcastFactory(
            rss=self.rss,
            last_updated=timezone.now(),
            cover_image=None,
            pub_date=None,
        )

        self.assertEqual(podcast.sync_rss_feed(), 0)
        podcast.refresh_from_db()

        self.assertFalse(podcast.pub_date)
        self.assertFalse(podcast.cover_image)

        self.assertNotEqual(podcast.title, "Mysterious Universe")
        self.assertEqual(podcast.episode_set.count(), 0)

    @patch("requests.head", autospec=True, return_value=MockHeaderResponse())
    @patch("requests.get", autospec=True, return_value=MockResponse("rss_mock.xml"))
    def test_parse_existing_episodes(self, *mocks: Mock) -> None:
        podcast = PodcastFactory(
            rss=self.rss,
            last_updated=None,
            pub_date=None,
        )

        EpisodeFactory(podcast=podcast, guid="https://mysteriousuniverse.org/?p=168097")
        EpisodeFactory(podcast=podcast, guid="https://mysteriousuniverse.org/?p=167650")
        EpisodeFactory(podcast=podcast, guid="https://mysteriousuniverse.org/?p=167326")

        # check episode not present is deleted
        EpisodeFactory(podcast=podcast, guid="some-random")

        self.assertEqual(podcast.sync_rss_feed(), 17)
        podcast.refresh_from_db()

        self.assertEqual(podcast.episode_set.count(), 20)
        self.assertFalse(Episode.objects.filter(guid="some-random").exists())


class AudioModelTests(SimpleTestCase):
    url = "https://www.podtrac.com/pts/redirect.mp3/traffic.megaphone.fm/TSK8060512733.mp3"

    def test_audio(self) -> None:
        Audio(type="audio/mpeg", url=self.url)

    def test_not_audio(self) -> None:
        self.assertRaises(ValidationError, Audio, type="text/xml", url=self.url)


class FeedModelTests(SimpleTestCase):
    website = "http://reddit.com"

    def setUp(self) -> None:
        self.item = Item(
            audio=Audio(
                type="audio/mpeg",
                rel="enclosure",
                url="https://www.podtrac.com/pts/redirect.mp3/traffic.megaphone.fm/TSK8060512733.mp3",
            ),
            title="test",
            guid="test",
            raw_pub_date="Fri, 12 Jun 2020 17:33:46 +0000",
            duration="2000",
        )

    def test_language(self) -> None:

        feed = Feed(
            title="test",
            description="test",
            items=[self.item],
            creators=set(),
            image=None,
            link=self.website,
            language="en-gb",
            categories=[],
        )

        self.assertEqual(feed.language, "en")

    def test_language_with_spaces(self) -> None:

        feed = Feed(
            title="test",
            description="test",
            items=[self.item],
            creators=set(),
            image=None,
            link=self.website,
            language=" en-us",
            categories=[],
        )

        self.assertEqual(feed.language, "en")

    def test_language_with_single_value(self) -> None:

        feed = Feed(
            title="test",
            description="test",
            items=[self.item],
            creators=set(),
            image=None,
            link=self.website,
            language="fi",
            categories=[],
        )

        self.assertEqual(feed.language, "fi")

    def test_language_with_empty(self) -> None:

        feed = Feed(
            title="test",
            description="test",
            items=[self.item],
            creators=set(),
            image=None,
            link=self.website,
            language="",
            categories=[],
        )

        self.assertEqual(feed.language, "en")

    def test_valid_link(self) -> None:
        feed = Feed(
            title="test",
            description="test",
            items=[self.item],
            creators=set(),
            image=None,
            link=self.website,
            categories=[],
        )

        self.assertEqual(feed.link, self.website)

    def test_empty_link(self) -> None:
        feed = Feed(
            title="test",
            description="test",
            items=[self.item],
            creators=set(),
            image=None,
            link="",
            categories=[],
        )

        self.assertEqual(feed.link, "")

    def test_missing_http(self) -> None:
        feed = Feed(
            title="test",
            description="test",
            items=[self.item],
            creators=set(),
            image=None,
            link="politicology.com",
            categories=[],
        )

        self.assertEqual(feed.link, "http://politicology.com")


class ParseDateTests(SimpleTestCase):
    def test_parse_date_if_valid(self) -> None:
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=pytz.UTC)
        self.assertEqual(parse_date("Fri, 19 Jun 2020 16:58:03 +0000"), dt)

    def test_parse_date_if_no_tz(self) -> None:
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=pytz.UTC)
        self.assertEqual(parse_date("Fri, 19 Jun 2020 16:58:03"), dt)

    def test_parse_date_if_invalid(self) -> None:
        self.assertEqual(parse_date("Fri, 33 June 2020 16:58:03 +0000"), None)
