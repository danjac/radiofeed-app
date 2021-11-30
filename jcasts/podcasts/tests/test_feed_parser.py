import http
import pathlib

from datetime import timedelta

import pytest
import requests

from django.utils import timezone

from jcasts.episodes.factories import EpisodeFactory
from jcasts.episodes.models import Episode
from jcasts.podcasts import feed_parser
from jcasts.podcasts.date_parser import parse_date
from jcasts.podcasts.factories import (
    CategoryFactory,
    FeedFactory,
    ItemFactory,
    PodcastFactory,
)
from jcasts.podcasts.models import Podcast
from jcasts.podcasts.rss_parser import Feed, Item


@pytest.fixture
def mock_rq(mocker):
    mocker.patch("rq.worker.Worker.count", return_value=2)
    mocker.patch("django_rq.get_queue")


@pytest.fixture
def feed():
    return Feed(**FeedFactory())


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
        raise requests.HTTPError(response=self)


class TestGetScheduledLimit:
    def test_no_queued_items(self, db, mock_rq):
        assert feed_parser.get_scheduled_limit(timedelta(minutes=12)) == 720

    def test_with_queued_items(self, db, mock_rq):
        PodcastFactory.create_batch(10, queued=timezone.now())
        assert feed_parser.get_scheduled_limit(timedelta(minutes=12)) == 710


class TestParsePubDates:
    def test_no_items(self, podcast, feed):
        pub_date, frequency, modifier = feed_parser.parse_pub_dates(podcast, feed, [])

        assert pub_date == podcast.pub_date
        assert frequency > timedelta(hours=24)
        assert modifier == 0.06

    def test_new_pub_dates(self, podcast, feed):

        now = timezone.now()

        items = [
            Item(**ItemFactory(pub_date=now - timedelta(days=3))),
            Item(**ItemFactory(pub_date=now - timedelta(days=6))),
            Item(**ItemFactory(pub_date=now - timedelta(days=9))),
        ]

        pub_date, frequency, modifier = feed_parser.parse_pub_dates(
            podcast, feed, items
        )

        assert pub_date == items[0].pub_date
        assert frequency == timedelta(days=3, seconds=12960)
        assert modifier == 0.06

    def test_no_new_pub_dates(self, db, feed):
        podcast = PodcastFactory(frequency=timedelta(hours=24))

        items = [Item(**ItemFactory(pub_date=podcast.pub_date))]

        pub_date, frequency, modifier = feed_parser.parse_pub_dates(
            podcast, feed, items
        )

        assert pub_date == podcast.pub_date
        assert frequency > timedelta(hours=24)
        assert modifier == 0.06


class TestParseWebSub:

    hub = "https://amazinglybrilliant.superfeedr.com/"
    url = "https://podnews.net/rss"

    def test_no_websub_hub(self, feed):
        assert feed_parser.parse_websub(Podcast(), MockResponse(), feed) == (
            None,
            None,
            None,
        )

    def test_websub_hub_in_feed(self):
        feed = Feed(**FeedFactory(websub_hub=self.hub))
        assert feed_parser.parse_websub(Podcast(), MockResponse(), feed) == (
            self.hub,
            None,
            None,
        )

    def test_websub_hub_in_headers(self):
        feed = Feed(**FeedFactory())
        links = {
            "hub": self.hub,
            "self": self.url,
        }
        assert feed_parser.parse_websub(Podcast(), MockResponse(links=links), feed) == (
            self.hub,
            self.url,
            None,
        )

    def test_websub_hub_in_headers_missing_url(self):
        feed = Feed(**FeedFactory())
        links = {"hub": self.hub}
        assert feed_parser.parse_websub(Podcast(), MockResponse(links=links), feed) == (
            None,
            None,
            None,
        )

    def test_websub_hub_in_feed_no_change(self):
        feed = Feed(**FeedFactory(websub_hub=self.hub))
        podcast = Podcast(
            websub_hub=self.hub, websub_status=Podcast.WebSubStatus.ACTIVE
        )
        assert feed_parser.parse_websub(podcast, MockResponse(), feed) == (
            self.hub,
            None,
            Podcast.WebSubStatus.ACTIVE,
        )

    def test_websub_hub_in_feed_change(self):
        feed = Feed(**FeedFactory(websub_hub=self.hub))
        podcast = Podcast(
            websub_hub="https://other-hub.com/",
            websub_status=Podcast.WebSubStatus.ACTIVE,
        )
        assert feed_parser.parse_websub(podcast, MockResponse(), feed) == (
            self.hub,
            None,
            None,
        )

    def test_websub_hub_in_headers_change(self):
        feed = Feed(**FeedFactory())
        podcast = Podcast(
            websub_hub="https://other-hub.com/",
            websub_status=Podcast.WebSubStatus.ACTIVE,
        )
        links = {
            "hub": self.hub,
            "self": self.url,
        }
        assert feed_parser.parse_websub(podcast, MockResponse(links=links), feed) == (
            self.hub,
            self.url,
            None,
        )


class TestFeedHeaders:
    def test_has_etag(self):
        podcast = Podcast(etag="abc123")
        headers = feed_parser.get_feed_headers(podcast)
        assert headers["If-None-Match"] == f'"{podcast.etag}"'

    def test_is_modified(self):
        podcast = Podcast(modified=timezone.now())
        headers = feed_parser.get_feed_headers(podcast)
        assert headers["If-Modified-Since"]


class TestParsePodcastFeeds:
    def test_parse_scheduled_feeds(self, db, mock_parse_podcast_feed, mock_rq):

        now = timezone.now()

        # inactive
        PodcastFactory(active=False)

        # not scheduled yet
        PodcastFactory(
            pub_date=now, frequency=timedelta(days=1), parsed=now - timedelta(days=1)
        )

        # queued
        PodcastFactory(
            queued=now,
            pub_date=now - timedelta(days=3),
            frequency=timedelta(hours=1),
            parsed=now - timedelta(days=1),
        )

        # scheduled
        podcast = PodcastFactory(
            pub_date=now - timedelta(days=3),
            frequency=timedelta(hours=1),
            parsed=now - timedelta(days=1),
        )

        feed_parser.parse_scheduled_feeds(frequency=timedelta(hours=1))

        queued = Podcast.objects.filter(queued__isnull=False)

        assert queued.count() == 2

        assert podcast in queued
        assert len(mock_parse_podcast_feed.mock_calls) == 1


class TestParsePodcastFeed:

    mock_file = "rss_mock.xml"
    mock_http_get = "requests.get"
    rss = "https://mysteriousuniverse.org/feed/podcast/"
    redirect_rss = "https://example.com/test.xml"
    updated = "Wed, 01 Jul 2020 15:25:26 +0000"

    @pytest.fixture
    def new_podcast(self, db):
        now = timezone.now()
        return PodcastFactory(
            cover_url=None,
            pub_date=now,
            queued=now,
        )

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

        feed_parser.get_categories_dict.cache_clear()

    def get_rss_content(self, filename=""):
        return open(
            pathlib.Path(__file__).parent / "mocks" / (filename or self.mock_file),
            "rb",
        ).read()

    def test_parse_podcast_feed_podcast_not_found(self, db):
        result = feed_parser.parse_podcast_feed(1234)
        assert result.success is False

        with pytest.raises(Podcast.DoesNotExist):
            result.raise_exception()

    def test_parse_podcast_feed_ok(self, mocker, new_podcast, categories):

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
        assert feed_parser.parse_podcast_feed(new_podcast.id)

        # new episodes: 19
        assert Episode.objects.count() == 20

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        new_podcast.refresh_from_db()

        assert new_podcast.rss
        assert new_podcast.active
        assert new_podcast.num_failures == 0
        assert new_podcast.title == "Mysterious Universe"

        assert (
            new_podcast.description == "Blog and Podcast specializing in offbeat news"
        )

        assert new_podcast.owner == "8th Kind"

        assert new_podcast.modified
        assert new_podcast.modified.day == 1
        assert new_podcast.modified.month == 7
        assert new_podcast.modified.year == 2020
        assert not new_podcast.queued
        assert new_podcast.result == Podcast.Result.SUCCESS

        assert new_podcast.parsed

        assert new_podcast.etag
        assert new_podcast.explicit
        assert new_podcast.cover_url

        assert new_podcast.pub_date == parse_date("Fri, 19 Jun 2020 16:58:03 +0000")

        assigned_categories = [c.name for c in new_podcast.categories.all()]

        assert "Science" in assigned_categories
        assert "Religion & Spirituality" in assigned_categories
        assert "Society & Culture" in assigned_categories
        assert "Philosophy" in assigned_categories

    def test_parse_podcast_feed_complete(self, mocker, new_podcast, categories):

        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        EpisodeFactory(podcast=new_podcast, guid=episode_guid, title=episode_title)

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=new_podcast.rss,
                content=self.get_rss_content("rss_mock_complete.xml"),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )
        assert feed_parser.parse_podcast_feed(new_podcast.id)

        # new episodes: 19
        assert Episode.objects.count() == 20

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        new_podcast.refresh_from_db()

        assert new_podcast.rss
        assert not new_podcast.active
        assert new_podcast.num_failures == 0
        assert new_podcast.title == "Mysterious Universe"

        assert (
            new_podcast.description == "Blog and Podcast specializing in offbeat news"
        )

        assert new_podcast.owner == "8th Kind"

        assert new_podcast.modified
        assert new_podcast.modified.day == 1
        assert new_podcast.modified.month == 7
        assert new_podcast.modified.year == 2020
        assert not new_podcast.queued
        assert new_podcast.result == Podcast.Result.SUCCESS

        assert new_podcast.parsed

        assert new_podcast.etag
        assert new_podcast.explicit
        assert new_podcast.cover_url

        assert new_podcast.pub_date == parse_date("Fri, 19 Jun 2020 16:58:03 +0000")

        assigned_categories = [c.name for c in new_podcast.categories.all()]

        assert "Science" in assigned_categories
        assert "Religion & Spirituality" in assigned_categories
        assert "Society & Culture" in assigned_categories
        assert "Philosophy" in assigned_categories

    def test_parse_podcast_feed_permanent_redirect(
        self, mocker, new_podcast, categories
    ):
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
        assert feed_parser.parse_podcast_feed(new_podcast.id)
        assert Episode.objects.filter(podcast=new_podcast).count() == 20

        new_podcast.refresh_from_db()

        assert new_podcast.rss == self.redirect_rss
        assert new_podcast.active
        assert new_podcast.num_failures == 0
        assert new_podcast.modified
        assert new_podcast.parsed
        assert not new_podcast.queued

    def test_parse_podcast_feed_permanent_redirect_url_taken(
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
        assert not feed_parser.parse_podcast_feed(new_podcast.id)

        new_podcast.refresh_from_db()

        assert new_podcast.rss == current_rss
        assert new_podcast.num_failures == 0
        assert not new_podcast.active
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert new_podcast.result == Podcast.Result.DUPLICATE_FEED

    def test_parse_no_podcasts(self, mocker, new_podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=new_podcast.rss,
                content=self.get_rss_content("rss_no_podcasts_mock.xml"),
            ),
        )

        result = feed_parser.parse_podcast_feed(new_podcast.id)
        assert not result
        with pytest.raises(ValueError):
            result.raise_exception()

        new_podcast.refresh_from_db()
        assert new_podcast.active
        assert new_podcast.num_failures == 1
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert new_podcast.result == Podcast.Result.INVALID_RSS

    def test_parse_empty_feed(self, mocker, new_podcast, categories):

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=new_podcast.rss,
                content=self.get_rss_content("rss_empty_mock.xml"),
            ),
        )

        result = feed_parser.parse_podcast_feed(new_podcast.id)
        assert not result
        with pytest.raises(ValueError):
            result.raise_exception()

        new_podcast.refresh_from_db()
        assert new_podcast.active
        assert new_podcast.num_failures == 1
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert new_podcast.result == Podcast.Result.INVALID_RSS

    def test_parse_podcast_feed_not_modified(self, mocker, new_podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                new_podcast.rss, status=http.HTTPStatus.NOT_MODIFIED
            ),
        )
        assert not feed_parser.parse_podcast_feed(new_podcast.id)

        new_podcast.refresh_from_db()
        assert new_podcast.active
        assert new_podcast.modified is None
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert new_podcast.result == Podcast.Result.NOT_MODIFIED

    def test_parse_podcast_feed_error(self, mocker, new_podcast, categories):
        mocker.patch(self.mock_http_get, side_effect=requests.RequestException)

        result = feed_parser.parse_podcast_feed(new_podcast.id)
        assert result.success is False

        with pytest.raises(requests.RequestException):
            result.raise_exception()

        new_podcast.refresh_from_db()
        assert new_podcast.active
        assert new_podcast.num_failures == 1
        assert new_podcast.http_status is None
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert new_podcast.result == Podcast.Result.NETWORK_ERROR

    def test_parse_podcast_feed_http_gone(self, mocker, new_podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(status=http.HTTPStatus.GONE),
        )
        result = feed_parser.parse_podcast_feed(new_podcast.id)
        # no exception set for http errors
        result.raise_exception()

        assert result.success is False

        new_podcast.refresh_from_db()

        assert not new_podcast.active
        assert new_podcast.num_failures == 0
        assert new_podcast.http_status == http.HTTPStatus.GONE
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert new_podcast.result == Podcast.Result.HTTP_ERROR

    def test_parse_podcast_feed_http_server_error(
        self, mocker, new_podcast, categories
    ):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(status=http.HTTPStatus.INTERNAL_SERVER_ERROR),
        )
        result = feed_parser.parse_podcast_feed(new_podcast.id)
        # no exception set for http errors
        result.raise_exception()

        assert result.success is False

        new_podcast.refresh_from_db()

        assert new_podcast.active
        assert new_podcast.num_failures == 1
        assert new_podcast.http_status == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert new_podcast.result == Podcast.Result.HTTP_ERROR

    def test_parse_podcast_feed_http_server_error_no_pub_date(
        self, mocker, new_podcast, categories
    ):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(status=http.HTTPStatus.INTERNAL_SERVER_ERROR),
        )
        new_podcast.pub_date = None
        new_podcast.save()

        result = feed_parser.parse_podcast_feed(new_podcast.id)
        # no exception set for http errors
        result.raise_exception()

        assert result.success is False

        new_podcast.refresh_from_db()

        assert new_podcast.active
        assert new_podcast.num_failures == 1
        assert new_podcast.http_status == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert new_podcast.result == Podcast.Result.HTTP_ERROR
