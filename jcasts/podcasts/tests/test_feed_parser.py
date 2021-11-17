import http
import pathlib

from datetime import timedelta

import pytest
import requests

from django.utils import timezone

from jcasts.episodes.factories import EpisodeFactory
from jcasts.episodes.models import Episode
from jcasts.podcasts.date_parser import parse_date
from jcasts.podcasts.factories import (
    CategoryFactory,
    FeedFactory,
    ItemFactory,
    PodcastFactory,
)
from jcasts.podcasts.feed_parser import (
    get_categories_dict,
    get_feed_headers,
    is_feed_changed,
    parse_podcast_feed,
    parse_podcast_feeds,
    parse_pub_dates,
)
from jcasts.podcasts.models import Podcast
from jcasts.podcasts.rss_parser import Feed, Item
from jcasts.podcasts.scheduler import DEFAULT_MODIFIER


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


class TestParsePubDates:
    @pytest.fixture
    def feed(self):
        return Feed(**FeedFactory())

    def test_no_items(self, podcast, feed):
        (
            pub_date,
            scheduled,
            frequency,
            modifier,
        ) = parse_pub_dates(podcast, feed, [])

        assert pub_date == podcast.pub_date
        assert frequency
        assert scheduled
        assert modifier > DEFAULT_MODIFIER

    def test_new_pub_dates(self, podcast, feed):

        now = timezone.now()

        items = [
            Item(**ItemFactory(pub_date=now - timedelta(days=3))),
            Item(**ItemFactory(pub_date=now - timedelta(days=6))),
            Item(**ItemFactory(pub_date=now - timedelta(days=9))),
        ]

        (
            pub_date,
            scheduled,
            frequency,
            modifier,
        ) = parse_pub_dates(podcast, feed, items)

        assert pub_date == items[0].pub_date
        assert frequency
        assert scheduled
        assert modifier

    def test_no_new_pub_dates(self, db, feed):
        podcast = PodcastFactory(scheduled=timezone.now())

        items = [Item(**ItemFactory(pub_date=podcast.pub_date))]

        (
            pub_date,
            scheduled,
            frequency,
            modifier,
        ) = parse_pub_dates(podcast, feed, items)

        assert pub_date == podcast.pub_date
        assert scheduled
        assert frequency
        assert modifier


class TestIsFeedChanged:
    def test_feed_date_is_none(self):
        assert is_feed_changed(
            Podcast(last_build_date=timezone.now()),
            Feed(**FeedFactory(last_build_date=None)),
        )

    def test_podcast_date_is_none(self):
        assert is_feed_changed(
            Podcast(last_build_date=None),
            Feed(**FeedFactory(last_build_date=timezone.now())),
        )

    def test_different_podcast_and_feed_dates(self):
        now = timezone.now()
        assert is_feed_changed(
            Podcast(last_build_date=now - timedelta(days=3)),
            Feed(**FeedFactory(last_build_date=now)),
        )

    def test_same_podcast_and_feed_dates(self):
        now = timezone.now()
        assert not is_feed_changed(
            Podcast(last_build_date=now),
            Feed(**FeedFactory(last_build_date=now)),
        )


class TestFeedHeaders:
    def test_has_etag(self):
        podcast = Podcast(etag="abc123")
        headers = get_feed_headers(podcast)
        assert headers["If-None-Match"] == f'"{podcast.etag}"'

    def test_is_modified(self):
        podcast = Podcast(modified=timezone.now())
        headers = get_feed_headers(podcast)
        assert headers["If-Modified-Since"]


class TestSchedulePodcastFeeds:
    def test_with_frequency_none(self, db, mock_parse_podcast_feed):

        now = timezone.now()

        # inactive
        PodcastFactory(active=False)

        # queued
        PodcastFactory(scheduled=now - timedelta(days=3), queued=now)

        # not scheduled yet
        unscheduled = PodcastFactory(scheduled=now + timedelta(days=1))

        # scheduled
        scheduled = PodcastFactory(
            scheduled=now - timedelta(days=3),
        )

        parse_podcast_feeds()

        queued = Podcast.objects.filter(queued__isnull=False)

        assert queued.count() == 3

        assert scheduled in queued
        assert unscheduled in queued

        assert len(mock_parse_podcast_feed.mock_calls) == 2

    def test_with_frequency(self, db, mocker, mock_parse_podcast_feed):

        mocker.patch("rq.worker.Worker.count", return_value=2)
        mocker.patch("django_rq.get_queue")

        now = timezone.now()

        # inactive
        PodcastFactory(active=False)

        # not scheduled yet
        PodcastFactory(scheduled=now + timedelta(days=1))

        # queued
        PodcastFactory(scheduled=now - timedelta(days=3), queued=now)

        # scheduled
        podcast = PodcastFactory(
            scheduled=now - timedelta(days=3),
        )

        parse_podcast_feeds(frequency=timedelta(hours=1))

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
            scheduled=now,
            frequency_modifier=DEFAULT_MODIFIER,
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

        get_categories_dict.cache_clear()

    def get_rss_content(self, filename=""):
        return open(
            pathlib.Path(__file__).parent / "mocks" / (filename or self.mock_file),
            "rb",
        ).read()

    def test_parse_podcast_feed_podcast_not_found(self, db):
        result = parse_podcast_feed(1234)
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
        assert parse_podcast_feed(new_podcast.id)

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
        assert new_podcast.scheduled
        assert new_podcast.frequency_modifier
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
        assert parse_podcast_feed(new_podcast.id)

        # new episodes: 19
        assert Episode.objects.count() == 20

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        new_podcast.refresh_from_db()

        assert new_podcast.rss
        assert not new_podcast.active
        assert new_podcast.title == "Mysterious Universe"

        assert (
            new_podcast.description == "Blog and Podcast specializing in offbeat news"
        )

        assert new_podcast.owner == "8th Kind"

        assert new_podcast.modified
        assert new_podcast.modified.day == 1
        assert new_podcast.modified.month == 7
        assert new_podcast.modified.year == 2020
        assert new_podcast.scheduled
        assert new_podcast.frequency_modifier
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

    def test_parse_podcast_same_last_build_date(self, mocker, new_podcast):

        new_podcast.last_build_date = parse_date("Wed, 01 Jul 2020 15:25:26 +0000")
        new_podcast.save()

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
        assert not parse_podcast_feed(new_podcast.id)
        new_podcast.refresh_from_db()
        assert new_podcast.result == Podcast.Result.NOT_MODIFIED

    def test_parse_podcast_new_last_build_date(self, mocker, new_podcast, categories):

        new_podcast.last_build_date = parse_date("Tue, 30 Jun 2020 15:25:26 +0000")
        new_podcast.save()

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
        assert parse_podcast_feed(new_podcast.id)

    def test_parse_podcast_last_build_date_none(self, mocker, new_podcast, categories):

        new_podcast.last_build_date = None
        new_podcast.save()

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
        assert parse_podcast_feed(new_podcast.id)

    def test_parse_podcast_no_last_build_date(self, mocker, new_podcast, categories):

        new_podcast.last_build_date = parse_date("Tue, 30 Jun 2020 15:25:26 +0000")
        new_podcast.save()

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=new_podcast.rss,
                content=self.get_rss_content("rss_mock_no_build_date.xml"),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )
        assert parse_podcast_feed(new_podcast.id)

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
        assert parse_podcast_feed(new_podcast.id)
        assert Episode.objects.filter(podcast=new_podcast).count() == 20

        new_podcast.refresh_from_db()

        assert new_podcast.rss == self.redirect_rss
        assert new_podcast.modified
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert new_podcast.scheduled
        assert new_podcast.frequency_modifier

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
        assert not parse_podcast_feed(new_podcast.id)

        new_podcast.refresh_from_db()

        assert new_podcast.rss == current_rss
        assert not new_podcast.active
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert not new_podcast.scheduled
        assert not new_podcast.frequency_modifier
        assert new_podcast.result == Podcast.Result.DUPLICATE_FEED

    def test_parse_no_podcasts(self, mocker, new_podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=new_podcast.rss,
                content=self.get_rss_content("rss_no_podcasts_mock.xml"),
            ),
        )

        result = parse_podcast_feed(new_podcast.id)
        assert not result
        with pytest.raises(ValueError):
            result.raise_exception()

        new_podcast.refresh_from_db()
        assert not new_podcast.active
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert not new_podcast.scheduled
        assert not new_podcast.frequency_modifier
        assert new_podcast.result == Podcast.Result.INVALID_RSS

    def test_parse_empty_feed(self, mocker, new_podcast, categories):

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=new_podcast.rss,
                content=self.get_rss_content("rss_empty_mock.xml"),
            ),
        )

        result = parse_podcast_feed(new_podcast.id)
        assert not result
        with pytest.raises(ValueError):
            result.raise_exception()

        new_podcast.refresh_from_db()
        assert not new_podcast.active
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert not new_podcast.scheduled
        assert not new_podcast.frequency_modifier
        assert new_podcast.result == Podcast.Result.INVALID_RSS

    def test_parse_podcast_feed_not_modified(self, mocker, new_podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                new_podcast.rss, status=http.HTTPStatus.NOT_MODIFIED
            ),
        )
        assert not parse_podcast_feed(new_podcast.id)

        new_podcast.refresh_from_db()
        assert new_podcast.active
        assert new_podcast.modified is None
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert new_podcast.scheduled
        assert new_podcast.frequency_modifier > DEFAULT_MODIFIER
        assert new_podcast.result == Podcast.Result.NOT_MODIFIED

    def test_parse_podcast_feed_error(self, mocker, new_podcast, categories):
        mocker.patch(self.mock_http_get, side_effect=requests.RequestException)

        result = parse_podcast_feed(new_podcast.id)
        assert result.success is False

        with pytest.raises(requests.RequestException):
            result.raise_exception()

        new_podcast.refresh_from_db()
        assert new_podcast.active
        assert new_podcast.http_status is None
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert new_podcast.scheduled
        assert new_podcast.frequency_modifier
        assert new_podcast.result == Podcast.Result.NETWORK_ERROR

    def test_parse_podcast_feed_http_gone(self, mocker, new_podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(status=http.HTTPStatus.GONE),
        )
        result = parse_podcast_feed(new_podcast.id)
        # no exception set for http errors
        result.raise_exception()

        assert result.success is False

        new_podcast.refresh_from_db()

        assert not new_podcast.active
        assert new_podcast.http_status == http.HTTPStatus.GONE
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert not new_podcast.scheduled
        assert not new_podcast.frequency_modifier
        assert new_podcast.result == Podcast.Result.HTTP_ERROR

    def test_parse_podcast_feed_http_server_error(
        self, mocker, new_podcast, categories
    ):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(status=http.HTTPStatus.INTERNAL_SERVER_ERROR),
        )
        result = parse_podcast_feed(new_podcast.id)
        # no exception set for http errors
        result.raise_exception()

        assert result.success is False

        new_podcast.refresh_from_db()

        assert new_podcast.active
        assert new_podcast.http_status == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert new_podcast.scheduled
        assert new_podcast.frequency_modifier
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

        result = parse_podcast_feed(new_podcast.id)
        # no exception set for http errors
        result.raise_exception()

        assert result.success is False

        new_podcast.refresh_from_db()

        assert new_podcast.active
        assert new_podcast.http_status == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert new_podcast.scheduled
        assert new_podcast.frequency_modifier
        assert new_podcast.result == Podcast.Result.HTTP_ERROR
