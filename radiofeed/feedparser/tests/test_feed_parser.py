from __future__ import annotations

import datetime
import http
import pathlib

import pytest
import requests

from django.utils import timezone

from radiofeed.common.utils.crypto import make_content_hash
from radiofeed.common.utils.dates import parse_date
from radiofeed.episodes.factories import EpisodeFactory
from radiofeed.episodes.models import Episode
from radiofeed.feedparser.feed_parser import FeedParser, parse_feed
from radiofeed.podcasts.factories import CategoryFactory, PodcastFactory
from radiofeed.podcasts.models import Podcast


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


class TestFeedParser:

    mock_file = "rss_mock.xml"
    mock_http_get = "requests.get"
    rss = "https://mysteriousuniverse.org/feed/podcast/"
    redirect_rss = "https://example.com/test.xml"
    updated = "Wed, 01 Jul 2020 15:25:26 +0000"

    @pytest.fixture
    def categories(self):
        return [
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

    def get_rss_content(self, filename=""):
        return (
            pathlib.Path(__file__).parent / "mocks" / (filename or self.mock_file)
        ).read_bytes()

    def test_has_etag(self):
        podcast = Podcast(etag="abc123")
        headers = FeedParser(podcast)._get_feed_headers()
        assert headers["If-None-Match"] == f'"{podcast.etag}"'

    def test_is_modified(self):
        podcast = Podcast(modified=timezone.now())
        headers = FeedParser(podcast)._get_feed_headers()
        assert headers["If-Modified-Since"]

    def test_parse_unhandled_exception(self, podcast, mocker):

        mocker.patch(
            "radiofeed.feedparser.feed_parser.FeedParser.parse",
            side_effect=ValueError(),
        )

        assert not parse_feed(podcast)

        podcast.refresh_from_db()
        assert podcast.active
        assert podcast.parse_result is None

    def test_parse_rss_exception(self, podcast, mocker):

        mocker.patch(
            "radiofeed.feedparser.feed_parser.FeedParser._parse_rss",
            side_effect=ValueError(),
        )

        assert not parse_feed(podcast)

        podcast.refresh_from_db()
        assert podcast.active
        assert podcast.parse_result is None

    def test_parse_ok(self, db, mocker, categories):

        # set date to before latest
        podcast = PodcastFactory(
            pub_date=datetime.datetime(year=2020, month=3, day=1), num_retries=3
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
        assert parse_feed(podcast)

        # new episodes: 19
        assert Episode.objects.count() == 20

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.rss
        assert podcast.active
        assert podcast.parse_result == Podcast.ParseResult.SUCCESS
        assert podcast.num_retries == 0
        assert podcast.content_hash
        assert podcast.title == "Mysterious Universe"

        assert podcast.description == "Blog and Podcast specializing in offbeat news"
        assert podcast.owner == "8th Kind"

        assert (
            podcast.extracted_text
            == "mysterious universe blog specializing offbeat th kind science medicine science social science religion spirituality spirituality society culture philosophy mu tibetan zombie mu saber tooth tiger king mu kgb cop mu joshua cutchin timothy renner mu squid router mu jim bruton"
        )

        assert podcast.modified
        assert podcast.modified.day == 1
        assert podcast.modified.month == 7
        assert podcast.modified.year == 2020

        assert podcast.parsed

        assert podcast.etag
        assert podcast.explicit
        assert podcast.cover_url

        assert podcast.pub_date == parse_date("Fri, 19 Jun 2020 16:58:03 +0000")

        assert podcast.keywords == "science & medicine"

        assigned_categories = [c.name for c in podcast.categories.all()]

        assert "Science" in assigned_categories
        assert "Religion & Spirituality" in assigned_categories
        assert "Society & Culture" in assigned_categories
        assert "Philosophy" in assigned_categories

    def test_parse_high_num_episodes(self, db, mocker, categories):

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
        assert parse_feed(podcast)

        assert Episode.objects.count() == 4940

        podcast.refresh_from_db()

        assert podcast.rss
        assert podcast.active
        assert podcast.parse_result == Podcast.ParseResult.SUCCESS
        assert podcast.content_hash
        assert podcast.title == "Armstrong & Getty On Demand"

    def test_parse_ok_no_pub_date(self, db, mocker, categories):

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
        assert parse_feed(podcast)

        # new episodes: 19
        assert Episode.objects.count() == 20

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.rss
        assert podcast.active
        assert podcast.parse_result == Podcast.ParseResult.SUCCESS
        assert podcast.content_hash
        assert podcast.title == "Mysterious Universe"

        assert podcast.description == "Blog and Podcast specializing in offbeat news"

        assert podcast.owner == "8th Kind"

        assert podcast.modified
        assert podcast.modified.day == 1
        assert podcast.modified.month == 7
        assert podcast.modified.year == 2020

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

    def test_parse_same_content(self, db, mocker, categories):

        content = self.get_rss_content()
        podcast = PodcastFactory(content_hash=make_content_hash(content))

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

        assert not parse_feed(podcast)

        podcast.refresh_from_db()
        assert podcast.active
        assert podcast.parse_result == Podcast.ParseResult.NOT_MODIFIED
        assert podcast.modified is None
        assert podcast.parsed

    def test_parse_podcast_another_feed_same_content(self, mocker, podcast, categories):

        content = self.get_rss_content()

        PodcastFactory(content_hash=make_content_hash(content))

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
        assert not parse_feed(podcast)

        podcast.refresh_from_db()

        assert not podcast.active
        assert podcast.parse_result == Podcast.ParseResult.DUPLICATE_FEED
        assert podcast.modified is None
        assert podcast.parsed

    def test_parse_complete(self, mocker, podcast, categories):

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
        assert parse_feed(podcast)

        # new episodes: 19
        assert Episode.objects.count() == 20

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.rss
        assert not podcast.active
        assert podcast.parse_result == Podcast.ParseResult.COMPLETE
        assert podcast.title == "Mysterious Universe"

        assert podcast.description == "Blog and Podcast specializing in offbeat news"

        assert podcast.owner == "8th Kind"

        assert podcast.modified
        assert podcast.modified.day == 1
        assert podcast.modified.month == 7
        assert podcast.modified.year == 2020

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

    def test_parse_permanent_redirect(self, mocker, podcast, categories):
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
        assert parse_feed(podcast)
        assert Episode.objects.filter(podcast=podcast).count() == 20

        podcast.refresh_from_db()

        assert podcast.rss == self.redirect_rss
        assert podcast.active
        assert podcast.parse_result == Podcast.ParseResult.SUCCESS
        assert podcast.modified
        assert podcast.parsed

    def test_parse_permanent_redirect_url_taken(self, mocker, podcast, categories):
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
        assert not parse_feed(podcast)

        podcast.refresh_from_db()

        assert podcast.rss == current_rss
        assert not podcast.active
        assert podcast.parse_result == Podcast.ParseResult.DUPLICATE_FEED
        assert podcast.parsed

    def test_parse_no_podcasts(self, mocker, podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=podcast.rss,
                content=self.get_rss_content("rss_no_podcasts_mock.xml"),
            ),
        )

        assert not parse_feed(podcast)

        podcast.refresh_from_db()
        assert podcast.active
        assert podcast.parse_result == Podcast.ParseResult.RSS_PARSER_ERROR
        assert podcast.parsed
        assert podcast.num_retries == 1

    def test_parse_no_podcasts_max_retries(self, mocker, podcast, categories):

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=podcast.rss,
                content=self.get_rss_content("rss_no_podcasts_mock.xml"),
            ),
        )

        podcast.num_retries = 3

        assert not parse_feed(podcast)

        podcast.refresh_from_db()
        assert not podcast.active
        assert podcast.parse_result == Podcast.ParseResult.RSS_PARSER_ERROR
        assert podcast.parsed
        assert podcast.num_retries == 4

    def test_parse_empty_feed(self, mocker, podcast, categories):

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=podcast.rss,
                content=self.get_rss_content("rss_empty_mock.xml"),
            ),
        )

        assert not parse_feed(podcast)

        podcast.refresh_from_db()
        assert podcast.active
        assert podcast.parse_result == Podcast.ParseResult.RSS_PARSER_ERROR
        assert podcast.parsed
        assert podcast.num_retries == 1

    def test_parse_not_modified(self, mocker, podcast, categories):

        podcast.num_retries = 1
        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(podcast.rss, status=http.HTTPStatus.NOT_MODIFIED),
        )
        assert not parse_feed(podcast)

        podcast.refresh_from_db()
        assert podcast.active
        assert podcast.parse_result == Podcast.ParseResult.NOT_MODIFIED
        assert podcast.modified is None
        assert podcast.parsed
        assert podcast.num_retries == 0

    def test_parse_http_gone(self, mocker, podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(status=http.HTTPStatus.GONE),
        )
        assert not parse_feed(podcast)

        podcast.refresh_from_db()

        assert not podcast.active
        assert podcast.http_status == http.HTTPStatus.GONE
        assert podcast.parse_result == Podcast.ParseResult.COMPLETE
        assert podcast.parsed

    def test_parse_http_server_error(self, mocker, podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(status=http.HTTPStatus.INTERNAL_SERVER_ERROR),
        )

        assert not parse_feed(podcast)

        podcast.refresh_from_db()

        assert podcast.active
        assert podcast.http_status == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert podcast.parse_result == Podcast.ParseResult.HTTP_ERROR
        assert podcast.parsed
        assert podcast.num_retries == 1

    def test_parse_http_server_error_max_retries(self, mocker, podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(status=http.HTTPStatus.INTERNAL_SERVER_ERROR),
        )

        podcast.num_retries = 3

        assert not parse_feed(podcast)

        podcast.refresh_from_db()

        assert not podcast.active
        assert podcast.http_status == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert podcast.parse_result == Podcast.ParseResult.HTTP_ERROR
        assert podcast.parsed
        assert podcast.num_retries == 4

    def test_parse_http_server_error_no_pub_date(self, mocker, podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(status=http.HTTPStatus.INTERNAL_SERVER_ERROR),
        )
        podcast.pub_date = None
        podcast.save()

        assert not parse_feed(podcast)

        podcast.refresh_from_db()

        assert podcast.active
        assert podcast.http_status == http.HTTPStatus.INTERNAL_SERVER_ERROR
        assert podcast.parse_result == Podcast.ParseResult.HTTP_ERROR
        assert podcast.parsed
