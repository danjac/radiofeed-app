import http
import pathlib

import pytest
import requests

from django.utils import timezone

from jcasts.episodes.factories import EpisodeFactory
from jcasts.episodes.models import Episode
from jcasts.podcasts.factories import CategoryFactory, PodcastFactory
from jcasts.podcasts.models import Podcast
from jcasts.podcasts.parsers import feed_parser
from jcasts.podcasts.parsers.date_parser import parse_date


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


class TestFeedHeaders:
    def test_has_etag(self):
        podcast = Podcast(etag="abc123")
        headers = feed_parser.get_feed_headers(podcast)
        assert headers["If-None-Match"] == f'"{podcast.etag}"'

    def test_is_modified(self):
        podcast = Podcast(modified=timezone.now())
        headers = feed_parser.get_feed_headers(podcast)
        assert headers["If-Modified-Since"]


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
