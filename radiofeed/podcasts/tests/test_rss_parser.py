# Standard Library
import datetime
import json
import pathlib
import uuid

# Django
from django.utils import timezone

# Third Party Libraries
import pytest
import pytz
import requests

# RadioFeed
from radiofeed.episodes.factories import EpisodeFactory

# Local
from ..factories import CategoryFactory, PodcastFactory
from ..rss_parser import RssParser, get_categories_dict
from ..rss_parser.date_parser import parse_date
from ..rss_parser.models import Audio, Feed, Item

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="function")
def clear_categories_cache():
    get_categories_dict.cache_clear()


@pytest.fixture
def item():
    return Item(
        audio=Audio(
            type="audio/mpeg",
            url="https://www.podtrac.com/pts/redirect.mp3/traffic.megaphone.fm/TSK8060512733.mp3",
        ),
        title="test",
        guid="test",
        pub_date=timezone.now(),
        duration="2000",
    )


class BaseMockResponse:
    def __init__(self, raises=False):
        self.raises = raises

    def raise_for_status(self):
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
    def __init__(self, mock_file=None, raises=False):
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

    def json(self):
        return json.loads(self.content)


class TestParseDate:
    def test_parse_date_if_valid(self):
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=pytz.UTC)
        assert parse_date("Fri, 19 Jun 2020 16:58:03 +0000") == dt

    def test_parse_date_if_no_tz(self):
        dt = datetime.datetime(2020, 6, 19, 16, 58, 3, tzinfo=pytz.UTC)
        assert parse_date("Fri, 19 Jun 2020 16:58:03") == dt

    def test_parse_date_if_invalid(self):
        assert parse_date("Fri, 33 June 2020 16:58:03 +0000") is None


class TestRssParser:
    def test_parse_error(self, podcast, mocker, clear_categories_cache):
        mocker.patch("requests.head", side_effect=requests.RequestException)
        with pytest.raises(requests.RequestException):
            RssParser.parse_from_podcast(podcast)
            podcast.refresh_from_db()

        assert podcast.num_retries == 1

    def test_parse(self, mocker, clear_categories_cache):
        mocker.patch("requests.head", return_value=MockHeaderResponse())
        mocker.patch("requests.get", return_value=MockResponse("rss_mock.txt"))
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
            rss="https://mysteriousuniverse.org/feed/podcast/",
            last_updated=None,
            pub_date=None,
        )
        RssParser.parse_from_podcast(podcast)
        podcast.refresh_from_db()

        assert podcast.last_updated
        assert podcast.pub_date

        assert podcast.title == "Mysterious Universe"
        assert podcast.etag
        assert podcast.authors
        assert podcast.extracted_text
        assert podcast.categories.count() == 6
        assert podcast.episode_set.count() == 20

    def test_parse_if_already_updated(self, mocker, clear_categories_cache):
        mocker.patch("requests.head", return_value=MockHeaderResponse())
        mocker.patch("requests.get", return_value=MockResponse("rss_mock.txt"))

        podcast = PodcastFactory(
            rss="https://mysteriousuniverse.org/feed/podcast/",
            last_updated=timezone.now(),
            pub_date=None,
        )

        RssParser.parse_from_podcast(podcast)
        podcast.refresh_from_db()

        assert podcast.pub_date is None
        assert podcast.title != "Mysterious Universe"
        assert podcast.episode_set.count() == 0

    def test_parse_existing_episodes(self, mocker, clear_categories_cache):
        mocker.patch("requests.head", return_value=MockHeaderResponse())
        mocker.patch("requests.get", return_value=MockResponse("rss_mock.txt"))
        podcast = PodcastFactory(
            rss="https://mysteriousuniverse.org/feed/podcast/",
            last_updated=None,
            pub_date=None,
        )

        EpisodeFactory(podcast=podcast, guid="https://mysteriousuniverse.org/?p=168097")
        EpisodeFactory(podcast=podcast, guid="https://mysteriousuniverse.org/?p=167650")
        EpisodeFactory(podcast=podcast, guid="https://mysteriousuniverse.org/?p=167326")

        RssParser.parse_from_podcast(podcast)
        podcast.refresh_from_db()
        assert podcast.episode_set.count() == 20


class TestFeedModel:
    def test_domain_link(self, item):
        feed = Feed(
            title="test",
            description="test",
            items=[item],
            authors=[],
            image=None,
            link="politicology.com",
            categories=[],
        )

        assert feed.link == "http://politicology.com"
