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
    FollowFactory,
    PodcastFactory,
)
from jcasts.podcasts.models import Podcast
from jcasts.podcasts.rss_parser import Feed


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


class TestEmptyQueue:
    def test_empty_queue(self, db, mock_feed_queue):

        podcast = PodcastFactory(queued=timezone.now(), feed_queue="feeds")
        mock_feed_queue.enqueued.append(podcast.id)

        feed_parser.empty_queue("feeds")

        assert podcast.id not in mock_feed_queue.enqueued
        podcast.refresh_from_db()

        assert podcast.feed_queue is None
        assert podcast.queued is None

    def test_empty_all_queues(self, db, mock_feed_queue):

        podcast = PodcastFactory(queued=timezone.now(), feed_queue="feeds")
        mock_feed_queue.enqueued.append(podcast.id)

        feed_parser.empty_all_queues()

        assert podcast.id not in mock_feed_queue.enqueued
        podcast.refresh_from_db()

        assert podcast.feed_queue is None
        assert podcast.queued is None


class TestEnqueue:
    def test_enqueue_one(self, db, mock_feed_queue, podcast):

        feed_parser.enqueue(podcast.id)
        assert podcast.id in mock_feed_queue.enqueued
        assert (
            Podcast.objects.filter(
                queued__isnull=False, feed_queue__isnull=False
            ).exists()
            is True
        )

    def test_enqueue_many(self, db, mock_feed_queue, podcast):

        feed_parser.enqueue(*[podcast.id])
        assert podcast.id in mock_feed_queue.enqueued
        assert (
            Podcast.objects.filter(
                queued__isnull=False, feed_queue__isnull=False
            ).exists()
            is True
        )

    def test_empty(self, db, mock_feed_queue):

        feed_parser.enqueue(*[])

        assert not mock_feed_queue.enqueued
        assert (
            Podcast.objects.filter(
                queued__isnull=False, feed_queue__isnull=False
            ).exists()
            is False
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


class TestParsePrimaryFeeds:
    @pytest.mark.parametrize(
        "active,success",
        [
            (True, True),
            (False, False),
        ],
    )
    def test_active(self, db, mock_feed_queue, active, success):

        podcast = PodcastFactory(active=active, promoted=True)

        feed_parser.parse_primary_feeds()

        Podcast.objects.filter(queued__isnull=False).exists() is success

        if success:
            assert podcast.id in mock_feed_queue.enqueued
        else:
            assert podcast.id not in mock_feed_queue.enqueued

    @pytest.mark.parametrize(
        "promoted,followed,success",
        [
            (True, True, True),
            (True, False, True),
            (False, True, True),
            (False, False, False),
        ],
    )
    def test_promoted_or_followed(
        self,
        db,
        mock_feed_queue,
        promoted,
        followed,
        success,
    ):

        podcast = PodcastFactory(promoted=promoted)

        if followed:
            FollowFactory(podcast=podcast)

        feed_parser.parse_primary_feeds()

        Podcast.objects.filter(queued__isnull=False).exists() is success

        if success:
            assert podcast.id in mock_feed_queue.enqueued
        else:
            assert podcast.id not in mock_feed_queue.enqueued

    @pytest.mark.parametrize(
        "queued,success",
        [
            (False, True),
            (True, False),
        ],
    )
    def test_queued(self, db, mock_feed_queue, queued, success):
        podcast = PodcastFactory(
            queued=timezone.now() if queued else None, promoted=True
        )

        feed_parser.parse_primary_feeds()

        if success:
            assert podcast.id in mock_feed_queue.enqueued
        else:
            assert podcast.id not in mock_feed_queue.enqueued


class TestParseSecondaryFeeds:
    @pytest.mark.parametrize(
        "pub_date,after,before,success",
        [
            (None, None, None, True),
            (None, timedelta(days=14), None, True),
            (timedelta(days=30), timedelta(days=14), None, False),
            (timedelta(days=30), None, timedelta(days=14), True),
            (timedelta(days=9), None, timedelta(days=14), False),
        ],
    )
    def test_time_values(
        self,
        db,
        mock_feed_queue,
        pub_date,
        after,
        before,
        success,
    ):

        now = timezone.now()

        podcast = PodcastFactory(
            pub_date=now - pub_date if pub_date else None,
        )

        feed_parser.parse_secondary_feeds(after=after, before=before)
        assert Podcast.objects.filter(queued__isnull=False).exists() is success

        if success:
            assert podcast.id in mock_feed_queue.enqueued
        else:
            assert podcast.id not in mock_feed_queue.enqueued

    @pytest.mark.parametrize(
        "active,success",
        [
            (True, True),
            (False, False),
        ],
    )
    def test_active(self, db, mock_feed_queue, active, success):

        podcast = PodcastFactory(active=active, pub_date=None)

        feed_parser.parse_secondary_feeds()

        Podcast.objects.filter(queued__isnull=False).exists() is success

        if success:
            assert podcast.id in mock_feed_queue.enqueued
        else:
            assert podcast.id not in mock_feed_queue.enqueued

    @pytest.mark.parametrize(
        "promoted,followed,success",
        [
            (True, True, False),
            (True, False, False),
            (False, True, False),
            (False, False, True),
        ],
    )
    def test_promoted_or_followed(
        self,
        db,
        mock_feed_queue,
        promoted,
        followed,
        success,
    ):

        podcast = PodcastFactory(promoted=promoted, pub_date=None)

        if followed:
            FollowFactory(podcast=podcast)

        feed_parser.parse_secondary_feeds()

        Podcast.objects.filter(queued__isnull=False).exists() is success

        if success:
            assert podcast.id in mock_feed_queue.enqueued
        else:
            assert podcast.id not in mock_feed_queue.enqueued

    @pytest.mark.parametrize(
        "queued,success",
        [
            (False, True),
            (True, False),
        ],
    )
    def test_queued(self, db, mock_feed_queue, queued, success):
        podcast = PodcastFactory(
            queued=timezone.now() if queued else None, pub_date=None
        )

        feed_parser.parse_secondary_feeds()

        if success:
            assert podcast.id in mock_feed_queue.enqueued
        else:
            assert podcast.id not in mock_feed_queue.enqueued


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
            feed_queue="feeds",
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
        assert new_podcast.content_hash
        assert new_podcast.errors == 0
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
        assert not new_podcast.feed_queue
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

    def test_parse_podcast_feed_same_content(self, mocker, new_podcast, categories):

        content = self.get_rss_content()

        Podcast.objects.filter(pk=new_podcast.id).update(
            content_hash=feed_parser.make_content_hash(content)
        )

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=new_podcast.rss,
                content=content,
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )
        assert not feed_parser.parse_podcast_feed(new_podcast.id)

        new_podcast.refresh_from_db()
        assert new_podcast.active
        assert new_podcast.modified is None
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert not new_podcast.feed_queue
        assert new_podcast.result == Podcast.Result.NOT_MODIFIED

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
        assert new_podcast.errors == 0
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
        assert not new_podcast.feed_queue
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
        assert new_podcast.errors == 0
        assert new_podcast.modified
        assert new_podcast.parsed
        assert not new_podcast.feed_queue
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
        assert new_podcast.errors == 0
        assert not new_podcast.active
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert not new_podcast.feed_queue
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
        assert new_podcast.errors == 1
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert not new_podcast.feed_queue
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
        assert new_podcast.errors == 1
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert not new_podcast.feed_queue
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
        assert not new_podcast.feed_queue
        assert new_podcast.result == Podcast.Result.NOT_MODIFIED

    def test_parse_podcast_feed_error(self, mocker, new_podcast, categories):
        mocker.patch(self.mock_http_get, side_effect=requests.RequestException)

        result = feed_parser.parse_podcast_feed(new_podcast.id)
        assert result.success is False

        with pytest.raises(requests.RequestException):
            result.raise_exception()

        new_podcast.refresh_from_db()
        assert new_podcast.active
        assert new_podcast.errors == 1
        assert new_podcast.http_status is None
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert not new_podcast.feed_queue
        assert new_podcast.result == Podcast.Result.NETWORK_ERROR

    def test_parse_podcast_feed_errors_past_limit(
        self, mocker, new_podcast, categories
    ):
        Podcast.objects.filter(pk=new_podcast.id).update(errors=11)

        mocker.patch(self.mock_http_get, side_effect=requests.RequestException)

        result = feed_parser.parse_podcast_feed(new_podcast.id)
        assert result.success is False

        with pytest.raises(requests.RequestException):
            result.raise_exception()

        new_podcast.refresh_from_db()
        assert not new_podcast.active
        assert new_podcast.errors == 12
        assert new_podcast.http_status is None
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert not new_podcast.feed_queue
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
        assert new_podcast.errors == 0
        assert new_podcast.http_status == http.HTTPStatus.GONE
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert not new_podcast.feed_queue
        assert new_podcast.result == Podcast.Result.HTTP_ERROR

    def test_parse_podcast_feed_http_server_error(
        self, mocker, new_podcast, categories
    ):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(status=http.HTTPStatus.INTERNAL_SERVER_ERROR),
        )
        result = feed_parser.parse_podcast_feed(new_podcast.id)

        with pytest.raises(requests.HTTPError):
            result.raise_exception()

        assert result.success is False

        new_podcast.refresh_from_db()

        assert new_podcast.active
        assert new_podcast.errors == 1
        assert new_podcast.http_status == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert not new_podcast.feed_queue
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

        with pytest.raises(requests.HTTPError):
            result.raise_exception()

        assert result.success is False

        new_podcast.refresh_from_db()

        assert new_podcast.active
        assert new_podcast.errors == 1
        assert new_podcast.http_status == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert new_podcast.parsed
        assert not new_podcast.queued
        assert not new_podcast.feed_queue
        assert new_podcast.result == Podcast.Result.HTTP_ERROR
