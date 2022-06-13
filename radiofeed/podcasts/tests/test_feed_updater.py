import datetime
import http
import pathlib

from datetime import timedelta
from unittest import mock

import pytest
import requests

from django.utils import timezone

from radiofeed.episodes.factories import EpisodeFactory
from radiofeed.episodes.models import Episode
from radiofeed.podcasts import feed_updater
from radiofeed.podcasts.factories import CategoryFactory, PodcastFactory
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.parsers.date_parser import parse_date


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


class TestEnqueue:
    def test_enqueue(self, mocker, podcast):

        mock_queue = mock.Mock()
        mocker.patch(
            "radiofeed.podcasts.feed_updater.get_queue",
            return_value=mock_queue,
        )
        feed_updater.enqueue(podcast.id)

        mock_queue.enqueue.assert_called_with(
            feed_updater.update,
            args=(podcast.id,),
        )
        podcast.refresh_from_db()
        assert podcast.queued


class TestSchedulePodcastFeedsForUpdate:
    def test_schedule(self, db, mocker):
        podcast = PodcastFactory(parsed=None, pub_date=None)

        patched = mocker.patch("radiofeed.podcasts.feed_updater.enqueue")

        assert feed_updater.schedule_podcast_feeds_for_update(100) == {podcast.id}
        patched.assert_called_with(podcast.id)


class TestGetPodcastFeedsForUpdate:
    @pytest.mark.parametrize(
        "active,queued,pub_date,parsed,exists",
        [
            (
                True,
                False,
                None,
                None,
                True,
            ),
            (
                False,
                False,
                None,
                None,
                False,
            ),
            (
                True,
                False,
                timedelta(hours=3),
                timedelta(hours=1),
                True,
            ),
            (
                True,
                True,
                timedelta(hours=3),
                timedelta(hours=1),
                False,
            ),
            (
                True,
                False,
                timedelta(hours=3),
                timedelta(minutes=30),
                False,
            ),
            (
                True,
                False,
                timedelta(days=3),
                timedelta(hours=3),
                True,
            ),
            (
                True,
                False,
                timedelta(days=3),
                timedelta(hours=1),
                False,
            ),
            (
                True,
                False,
                timedelta(days=8),
                timedelta(hours=8),
                True,
            ),
            (
                True,
                False,
                timedelta(days=8),
                timedelta(hours=9),
                True,
            ),
            (
                True,
                False,
                timedelta(days=14),
                timedelta(hours=8),
                False,
            ),
            (
                True,
                False,
                timedelta(days=15),
                timedelta(hours=8),
                False,
            ),
            (
                True,
                False,
                timedelta(days=15),
                timedelta(hours=24),
                True,
            ),
        ],
    )
    def test_get_podcast_feeds_for_update(
        self, db, mocker, active, queued, pub_date, parsed, exists
    ):
        now = timezone.now()

        PodcastFactory(
            active=active,
            queued=now if queued else None,
            pub_date=now - pub_date if pub_date else None,
            parsed=now - parsed if parsed else None,
        )

        assert feed_updater.get_podcast_feeds_for_update().exists() == exists


class TestFeedUpdater:

    mock_file = "rss_mock.xml"
    mock_http_get = "requests.get"
    rss = "https://mysteriousuniverse.org/feed/podcast/"
    redirect_rss = "https://example.com/test.xml"
    updated = "Wed, 01 Jul 2020 15:25:26 +0000"

    @pytest.fixture
    def categories(self):
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

        feed_updater.get_categories_dict.cache_clear()

    def test_podcast_does_not_exist(self, db):
        assert not feed_updater.update(1234)

    def test_has_etag(self):
        podcast = Podcast(etag="abc123")
        headers = feed_updater.FeedUpdater(podcast).get_feed_headers()
        assert headers["If-None-Match"] == f'"{podcast.etag}"'

    def test_is_modified(self):
        podcast = Podcast(modified=timezone.now())
        headers = feed_updater.FeedUpdater(podcast).get_feed_headers()
        assert headers["If-Modified-Since"]

    def get_rss_content(self, filename=""):
        return (
            pathlib.Path(__file__).parent / "mocks" / (filename or self.mock_file)
        ).read_bytes()

    def test_update_unhandled_exception(self, podcast, mocker):

        mocker.patch(
            "radiofeed.podcasts.feed_updater.FeedUpdater.parse_content",
            side_effect=ValueError,
        )
        with pytest.raises(ValueError):
            feed_updater.FeedUpdater(podcast).update()

    def test_update_ok(self, db, mocker, categories):

        # set date to before latest
        podcast = PodcastFactory(
            pub_date=datetime.datetime(year=2020, month=3, day=1), queued=timezone.now()
        )

        # set pub date to before latest Fri, 19 Jun 2020 16:58:03 +0000

        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        EpisodeFactory(podcast=podcast, guid=episode_guid, title=episode_title)

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=podcast.rss,
                content=self.get_rss_content(),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )
        assert feed_updater.update(podcast.id)

        # new episodes: 19
        assert Episode.objects.count() == 20

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.rss
        assert podcast.active
        assert podcast.queued is None
        assert podcast.content_hash
        assert podcast.errors == 0
        assert podcast.title == "Mysterious Universe"

        assert podcast.description == "Blog and Podcast specializing in offbeat news"

        assert podcast.owner == "8th Kind"

        assert podcast.modified
        assert podcast.modified.day == 1
        assert podcast.modified.month == 7
        assert podcast.modified.year == 2020
        assert podcast.result == Podcast.Result.SUCCESS

        assert podcast.parsed

        assert podcast.etag
        assert podcast.explicit
        assert podcast.cover_url

        assert podcast.pub_date == parse_date("Fri, 19 Jun 2020 16:58:03 +0000")

        assigned_categories = [c.name for c in podcast.categories.all()]

        assert "Science" in assigned_categories
        assert "Religion & Spirituality" in assigned_categories
        assert "Society & Culture" in assigned_categories
        assert "Philosophy" in assigned_categories

    def test_update_high_num_episodes(self, db, mocker, categories):

        podcast = PodcastFactory()

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=podcast.rss,
                content=self.get_rss_content("rss_high_num_episodes.xml"),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )
        assert feed_updater.update(podcast.id)

        assert Episode.objects.count() == 4940

        podcast.refresh_from_db()

        assert podcast.rss
        assert podcast.active
        assert podcast.content_hash
        assert podcast.errors == 0
        assert podcast.title == "Armstrong & Getty On Demand"

    def test_update_ok_no_pub_date(self, db, mocker, categories):

        podcast = PodcastFactory(pub_date=None)

        # set pub date to before latest Fri, 19 Jun 2020 16:58:03 +0000

        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        EpisodeFactory(podcast=podcast, guid=episode_guid, title=episode_title)

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=podcast.rss,
                content=self.get_rss_content(),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )
        assert feed_updater.update(podcast.id)

        # new episodes: 19
        assert Episode.objects.count() == 20

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.rss
        assert podcast.active
        assert podcast.content_hash
        assert podcast.errors == 0
        assert podcast.title == "Mysterious Universe"

        assert podcast.description == "Blog and Podcast specializing in offbeat news"

        assert podcast.owner == "8th Kind"

        assert podcast.modified
        assert podcast.modified.day == 1
        assert podcast.modified.month == 7
        assert podcast.modified.year == 2020
        assert podcast.result == Podcast.Result.SUCCESS

        assert podcast.parsed

        assert podcast.etag
        assert podcast.explicit
        assert podcast.cover_url

        assert podcast.pub_date == parse_date("Fri, 19 Jun 2020 16:58:03 +0000")

        assigned_categories = [c.name for c in podcast.categories.all()]

        assert "Science" in assigned_categories
        assert "Religion & Spirituality" in assigned_categories
        assert "Society & Culture" in assigned_categories
        assert "Philosophy" in assigned_categories

    def test_update_same_content(self, db, mocker, categories):

        content = self.get_rss_content()

        podcast = PodcastFactory(
            content_hash=feed_updater.make_content_hash(content), queued=timezone.now()
        )

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=podcast.rss,
                content=content,
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )
        assert not feed_updater.update(podcast.id)

        podcast.refresh_from_db()
        assert podcast.active
        assert podcast.modified is None
        assert podcast.queued is None
        assert podcast.parsed
        assert podcast.result == Podcast.Result.NOT_MODIFIED

    def test_parse_podcast_another_feed_same_content(self, mocker, podcast, categories):

        content = self.get_rss_content()

        PodcastFactory(content_hash=feed_updater.make_content_hash(content))

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=podcast.rss,
                content=content,
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )
        assert not feed_updater.update(podcast.id)

        podcast.refresh_from_db()

        assert not podcast.active
        assert podcast.modified is None
        assert podcast.parsed
        assert podcast.result == Podcast.Result.DUPLICATE_FEED

    def test_update_complete(self, mocker, podcast, categories):

        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        EpisodeFactory(podcast=podcast, guid=episode_guid, title=episode_title)

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=podcast.rss,
                content=self.get_rss_content("rss_mock_complete.xml"),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )
        assert feed_updater.update(podcast.id)

        # new episodes: 19
        assert Episode.objects.count() == 20

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.rss
        assert not podcast.active
        assert podcast.errors == 0
        assert podcast.title == "Mysterious Universe"

        assert podcast.description == "Blog and Podcast specializing in offbeat news"

        assert podcast.owner == "8th Kind"

        assert podcast.modified
        assert podcast.modified.day == 1
        assert podcast.modified.month == 7
        assert podcast.modified.year == 2020
        assert podcast.result == Podcast.Result.SUCCESS

        assert podcast.parsed

        assert podcast.etag
        assert podcast.explicit
        assert podcast.cover_url

        assert podcast.pub_date == parse_date("Fri, 19 Jun 2020 16:58:03 +0000")

        assigned_categories = [c.name for c in podcast.categories.all()]

        assert "Science" in assigned_categories
        assert "Religion & Spirituality" in assigned_categories
        assert "Society & Culture" in assigned_categories
        assert "Philosophy" in assigned_categories

    def test_update_permanent_redirect(self, mocker, podcast, categories):
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
        assert feed_updater.update(podcast.id)
        assert Episode.objects.filter(podcast=podcast).count() == 20

        podcast.refresh_from_db()

        assert podcast.rss == self.redirect_rss
        assert podcast.active
        assert podcast.errors == 0
        assert podcast.modified
        assert podcast.parsed

    def test_update_permanent_redirect_url_taken(self, mocker, podcast, categories):
        other = PodcastFactory(rss=self.redirect_rss)
        current_rss = podcast.rss

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
        assert not feed_updater.update(podcast.id)

        podcast.refresh_from_db()

        assert podcast.rss == current_rss
        assert podcast.errors == 0
        assert not podcast.active
        assert podcast.parsed
        assert podcast.result == Podcast.Result.DUPLICATE_FEED

    def test_parse_no_podcasts(self, mocker, podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=podcast.rss,
                content=self.get_rss_content("rss_no_podcasts_mock.xml"),
            ),
        )

        assert not feed_updater.update(podcast.id)

        podcast.refresh_from_db()
        assert podcast.active
        assert podcast.errors == 1
        assert podcast.parsed
        assert podcast.result == Podcast.Result.INVALID_RSS

    def test_parse_empty_feed(self, mocker, podcast, categories):

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=podcast.rss,
                content=self.get_rss_content("rss_empty_mock.xml"),
            ),
        )

        assert not feed_updater.update(podcast.id)

        podcast.refresh_from_db()
        assert podcast.active
        assert podcast.errors == 1
        assert podcast.parsed
        assert podcast.result == Podcast.Result.INVALID_RSS

    def test_update_not_modified(self, mocker, podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(podcast.rss, status=http.HTTPStatus.NOT_MODIFIED),
        )
        assert not feed_updater.update(podcast.id)

        podcast.refresh_from_db()
        assert podcast.active
        assert podcast.modified is None
        assert podcast.parsed
        assert podcast.result == Podcast.Result.NOT_MODIFIED

    def test_update_error(self, mocker, podcast, categories):
        mocker.patch(self.mock_http_get, side_effect=requests.RequestException)

        assert not feed_updater.update(podcast.id)

        podcast.refresh_from_db()
        assert podcast.active
        assert podcast.errors == 1
        assert podcast.http_status is None
        assert podcast.parsed
        assert podcast.result == Podcast.Result.NETWORK_ERROR

    def test_update_errors_past_limit(self, db, mocker, categories):

        podcast = PodcastFactory(errors=11)

        mocker.patch(self.mock_http_get, side_effect=requests.RequestException)

        assert not feed_updater.update(podcast.id)

        podcast.refresh_from_db()

        assert not podcast.active

        assert podcast.errors == 12
        assert podcast.http_status is None
        assert podcast.parsed
        assert podcast.result == Podcast.Result.NETWORK_ERROR

    def test_update_http_gone(self, mocker, podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(status=http.HTTPStatus.GONE),
        )
        assert not feed_updater.update(podcast.id)

        podcast.refresh_from_db()

        assert not podcast.active
        assert podcast.errors == 0
        assert podcast.http_status == http.HTTPStatus.GONE
        assert podcast.parsed
        assert podcast.result == Podcast.Result.REMOVED

    def test_update_http_server_error(self, mocker, podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(status=http.HTTPStatus.INTERNAL_SERVER_ERROR),
        )
        assert not feed_updater.update(podcast.id)

        podcast.refresh_from_db()

        assert podcast.active
        assert podcast.errors == 1
        assert podcast.http_status == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert podcast.parsed
        assert podcast.result == Podcast.Result.HTTP_ERROR

    def test_update_http_server_error_no_pub_date(self, mocker, podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(status=http.HTTPStatus.INTERNAL_SERVER_ERROR),
        )
        podcast.pub_date = None
        podcast.save()

        assert not feed_updater.update(podcast.id)

        podcast.refresh_from_db()

        assert podcast.active
        assert podcast.errors == 1
        assert podcast.http_status == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert podcast.parsed
        assert podcast.result == Podcast.Result.HTTP_ERROR
