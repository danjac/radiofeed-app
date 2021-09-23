import http
import pathlib
import uuid

from datetime import timedelta

import pytest
import requests

from django.utils import timezone

from jcasts.episodes.factories import EpisodeFactory
from jcasts.episodes.models import Episode
from jcasts.podcasts.date_parser import parse_date
from jcasts.podcasts.factories import CategoryFactory, PodcastFactory
from jcasts.podcasts.feed_parser import (
    get_categories_dict,
    get_feed_headers,
    parse_feed,
    parse_feed_fast,
    parse_podcast_feeds,
    reschedule,
)
from jcasts.podcasts.models import Podcast


class MockResponse:
    def __init__(
        self,
        url="",
        status=http.HTTPStatus.OK,
        content=b"",
        headers=None,
        links=None,
    ):
        self.url = url
        self.content = content
        self.headers = headers or {}
        self.links = links or {}
        self.status_code = status

    def raise_for_status(self):
        ...


class BadMockResponse(MockResponse):
    def raise_for_status(self):
        raise requests.HTTPError()


class TestParsePodcastFeeds:
    @pytest.mark.parametrize(
        "force_update,active,queued,scheduled,subscribed,result",
        [
            (False, True, False, timedelta(hours=-1), None, 1),
            (False, True, False, timedelta(hours=-1), timedelta(hours=24), 0),
            (False, True, False, timedelta(hours=-1), timedelta(hours=-24), 1),
            (False, True, True, timedelta(hours=-1), None, 0),
            (False, True, False, timedelta(hours=-1), None, 1),
            (False, True, False, timedelta(hours=1), None, 0),
            (True, True, False, timedelta(hours=1), None, 1),
            (True, True, False, None, None, 1),
            (True, False, False, None, None, 1),
            (False, False, False, None, None, 0),
        ],
    )
    def test_parse_podcast_feeds(
        self,
        db,
        mocker,
        force_update,
        active,
        queued,
        scheduled,
        subscribed,
        result,
    ):

        mock_parse_feed = mocker.patch("jcasts.podcasts.feed_parser.parse_feed.delay")

        now = timezone.now()
        PodcastFactory(
            active=active,
            scheduled=now + scheduled if scheduled else None,
            websub_token=uuid.uuid4() if subscribed else None,
            websub_hub="https://pubsubhubbub.com/" if subscribed else None,
            websub_subscribed=now + subscribed if subscribed else None,
            queued=now if queued else None,
        )
        assert parse_podcast_feeds(force_update=force_update) == result

        if result:
            mock_parse_feed.assert_called()
        else:
            mock_parse_feed.assert_not_called()


class TestParseFeedFast:
    def test_parse(self, podcast, mocker):
        class MockQueue:
            def enqueue(self, func, *args, **kwargs):
                pass

        mock_queue = mocker.patch("jcasts.podcasts.feed_parser.get_queue")
        parse_feed_fast(podcast)
        mock_queue.assert_called_with("feeds-fast")


class TestFeedHeaders:
    def test_has_etag(self):
        podcast = Podcast(etag="abc123")
        headers = get_feed_headers(podcast)
        assert headers["If-None-Match"] == f'"{podcast.etag}"'

    def test_is_modified(self):
        podcast = Podcast(modified=timezone.now())
        headers = get_feed_headers(podcast)
        assert headers["If-Modified-Since"]

    def test_force_update(self):
        podcast = Podcast(modified=timezone.now(), etag="12345")
        headers = get_feed_headers(podcast, force_update=True)
        assert "If-Modified-Since" not in headers
        assert "If-None-Match" not in headers


class TestParseFeed:

    mock_file = "rss_mock.xml"
    mock_http_get = "requests.get"
    rss = "https://mysteriousuniverse.org/feed/podcast/"
    redirect_rss = "https://example.com/test.xml"
    updated = "Wed, 01 Jul 2020 15:25:26 +0000"

    @pytest.fixture
    def new_podcast(self, db):
        return PodcastFactory(cover_url=None, pub_date=None, queued=timezone.now())

    @pytest.fixture
    def categories(self, db):
        yield [
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

        get_categories_dict.cache_clear()

    def get_rss_content(self, filename=""):
        return open(
            pathlib.Path(__file__).parent / "mocks" / (filename or self.mock_file), "rb"
        ).read()

    def test_parse_no_podcasts(self, mocker, new_podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=new_podcast.rss,
                content=self.get_rss_content("rss_no_podcasts_mock.xml"),
            ),
        )

        result = parse_feed(new_podcast.rss)
        assert not result
        with pytest.raises(ValueError):
            result.raise_exception()

        new_podcast.refresh_from_db()
        assert not new_podcast.active
        assert new_podcast.parsed
        assert new_podcast.queued is None

    def test_parse_empty_feed(self, mocker, new_podcast, categories):

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=new_podcast.rss,
                content=self.get_rss_content("rss_empty_mock.xml"),
            ),
        )

        result = parse_feed(new_podcast.rss)
        assert not result
        with pytest.raises(ValueError):
            result.raise_exception()

        new_podcast.refresh_from_db()
        assert not new_podcast.active
        assert new_podcast.parsed
        assert new_podcast.queued is None

    def test_parse_feed_podcast_not_found(self, db):
        result = parse_feed("https://example.com/rss.xml")
        assert result.success is False

        with pytest.raises(Podcast.DoesNotExist):
            result.raise_exception()

    def test_parse_feed_ok(self, mocker, new_podcast, categories):

        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        EpisodeFactory(podcast=new_podcast, guid=episode_guid, title=episode_title)

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=new_podcast.rss,
                content=self.get_rss_content(),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )
        assert parse_feed(new_podcast.rss)

        # new episodes: 19
        assert Episode.objects.count() == 20

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        new_podcast.refresh_from_db()

        assert new_podcast.rss
        assert new_podcast.active
        assert new_podcast.title == "Mysterious Universe"

        assert (
            new_podcast.description == "Blog and Podcast specializing in offbeat news"
        )

        assert new_podcast.owner == "8th Kind"

        assert new_podcast.modified
        assert new_podcast.modified.day == 1
        assert new_podcast.modified.month == 7
        assert new_podcast.modified.year == 2020
        assert new_podcast.parsed

        assert new_podcast.etag
        assert new_podcast.explicit
        assert new_podcast.cover_url

        assert new_podcast.pub_date == parse_date("Fri, 19 Jun 2020 16:58:03 +0000")
        assert new_podcast.queued is None

        assigned_categories = [c.name for c in new_podcast.categories.all()]

        assert "Science" in assigned_categories
        assert "Religion & Spirituality" in assigned_categories
        assert "Society & Culture" in assigned_categories
        assert "Philosophy" in assigned_categories

    def test_parse_feed_with_hub_in_link_header(self, mocker, new_podcast, categories):

        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        EpisodeFactory(podcast=new_podcast, guid=episode_guid, title=episode_title)

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=new_podcast.rss,
                content=self.get_rss_content(),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
                links={
                    "self": {"url": new_podcast.rss},
                    "hub": {"url": "https://pubsubhubbub.appspot.com/"},
                },
            ),
        )
        assert parse_feed(new_podcast.rss)
        new_podcast.refresh_from_db()
        assert new_podcast.websub_hub == "https://pubsubhubbub.appspot.com/"
        assert new_podcast.websub_url == new_podcast.rss

    def test_parse_feed_permanent_redirect(self, mocker, new_podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=self.redirect_rss,
                status=http.HTTPStatus.PERMANENT_REDIRECT,
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
                content=self.get_rss_content(),
            ),
        )
        assert parse_feed(new_podcast.rss)
        assert Episode.objects.filter(podcast=new_podcast).count() == 20

        new_podcast.refresh_from_db()

        assert new_podcast.rss == self.redirect_rss
        assert new_podcast.modified
        assert new_podcast.parsed
        assert new_podcast.queued is None

    def test_parse_feed_permanent_redirect_url_taken(
        self, mocker, new_podcast, categories
    ):
        other = PodcastFactory(rss=self.redirect_rss)
        current_rss = new_podcast.rss

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=other.rss,
                status=http.HTTPStatus.PERMANENT_REDIRECT,
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
                content=self.get_rss_content(),
            ),
        )
        assert not parse_feed(new_podcast.rss)

        new_podcast.refresh_from_db()

        assert new_podcast.rss == current_rss
        assert not new_podcast.active
        assert new_podcast.scheduled is None
        assert new_podcast.queued is None
        assert new_podcast.parsed

    def test_parse_feed_not_modified(self, mocker, new_podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                new_podcast.rss, status=http.HTTPStatus.NOT_MODIFIED
            ),
        )
        assert not parse_feed(new_podcast.rss)

        new_podcast.refresh_from_db()
        assert new_podcast.active
        assert new_podcast.modified is None
        assert new_podcast.queued is None

    def test_parse_feed_error(self, mocker, new_podcast, categories):
        mocker.patch(self.mock_http_get, side_effect=requests.RequestException)

        result = parse_feed(new_podcast.rss)
        assert result.success is False

        with pytest.raises(requests.RequestException):
            result.raise_exception()

        new_podcast.refresh_from_db()
        assert not new_podcast.active
        assert new_podcast.queued is None

    def test_parse_feed_gone(self, mocker, new_podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(new_podcast.rss, status=http.HTTPStatus.GONE),
        )
        result = parse_feed(new_podcast.rss)
        assert result.success is False

        with pytest.raises(requests.HTTPError):
            result.raise_exception()

        new_podcast.refresh_from_db()

        assert not new_podcast.active
        assert new_podcast.scheduled is None
        assert new_podcast.queued is None


class TestReschedule:
    def test_pub_date_none(self):
        assert reschedule(Podcast(pub_date=None)) is None

    def test_pub_date_min_one_hour(self):
        now = timezone.now()
        scheduled = reschedule(Podcast(pub_date=now))
        self.assert_hours_diff(scheduled - now, 1.0)

    def test_pub_date_not_none(self):
        now = timezone.now()
        pub_date = now - timedelta(days=3)
        scheduled = reschedule(Podcast(pub_date=pub_date))
        # 5% of 3 days == 3.6 hours
        self.assert_hours_diff(scheduled - now, 3.6)

    def test_scheduled_not_none(self):
        now = timezone.now()
        pub_date = now - timedelta(days=3)
        scheduled = reschedule(
            Podcast(pub_date=pub_date, scheduled=now - timedelta(hours=3))
        )
        # 5% of 3 days == 3.6 hours
        self.assert_hours_diff(scheduled - now, 3.45)

    def test_scheduled_lt_pub_date(self):
        now = timezone.now()
        pub_date = now - timedelta(days=1)
        scheduled = reschedule(
            Podcast(pub_date=pub_date, scheduled=now - timedelta(days=3))
        )
        # 5% of 3 days == 3.6 hours
        self.assert_hours_diff(scheduled - now, 1.2)

    def assert_hours_diff(self, delta, expected):
        assert delta.total_seconds() / 3600 == pytest.approx(expected)
