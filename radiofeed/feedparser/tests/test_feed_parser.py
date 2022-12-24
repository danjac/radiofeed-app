from __future__ import annotations

import http
import pathlib

from datetime import datetime

import httpx
import pytest

from django.utils import timezone

from radiofeed.episodes.factories import create_episode
from radiofeed.episodes.models import Episode
from radiofeed.feedparser.date_parser import parse_date
from radiofeed.feedparser.feed_parser import (
    Duplicate,
    FeedParser,
    Inaccessible,
    NotModified,
    get_categories,
    make_content_hash,
    parse_feed,
)
from radiofeed.feedparser.rss_parser import RssParserError
from radiofeed.podcasts.factories import create_category, create_podcast
from radiofeed.podcasts.models import Podcast


class MockClient:
    def __init__(self, response):
        self.response = response

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def get(self, *args, **kwargs):
        return self.response


def mock_response(url, status_code, **kwargs):
    return httpx.Response(status_code, request=httpx.Request("GET", url), **kwargs)


def mock_client(mocker, response):
    return mocker.patch("httpx.Client", return_value=MockClient(response))


class TestFeedParser:

    mock_file = "rss_mock.xml"
    rss = "https://mysteriousuniverse.org/feed/podcast/"
    redirect_rss = "https://example.com/test.xml"
    updated = "Wed, 01 Jul 2020 15:25:26 +0000"

    @pytest.fixture
    def categories(self):
        get_categories.cache_clear()

        yield [
            create_category(name=name)
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

        with httpx.Client() as session:
            with pytest.raises(ValueError):
                assert not parse_feed(podcast, session)

        podcast.refresh_from_db()
        assert podcast.active

    def test_parse_rss_exception(self, podcast, mocker):
        mocker.patch(
            "radiofeed.feedparser.rss_parser.parse_rss",
            side_effect=ValueError(),
        )

        mock_client(
            mocker,
            mock_response(
                podcast.rss,
                http.HTTPStatus.OK,
                content=self.get_rss_content(),
            ),
        )

        with httpx.Client() as session:
            with pytest.raises(ValueError):
                assert not parse_feed(podcast, session)

        podcast.refresh_from_db()
        assert podcast.active

    def test_parse_ok(self, mocker, db, categories):

        # set date to before latest
        podcast = create_podcast(
            pub_date=datetime(year=2020, month=3, day=1), num_retries=3
        )

        # set pub date to before latest Fri, 19 Jun 2020 16:58:03 +0000

        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        create_episode(podcast=podcast, guid=episode_guid, title=episode_title)

        mock_client(
            mocker,
            mock_response(
                podcast.rss,
                http.HTTPStatus.OK,
                content=self.get_rss_content(),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )

        with httpx.Client() as session:
            parse_feed(podcast, session)

        # new episodes: 19
        assert Episode.objects.count() == 20

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.rss
        assert podcast.active
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

    def test_parse_high_num_episodes(self, mocker, db, categories):

        podcast = create_podcast()

        mock_client(
            mocker,
            mock_response(
                podcast.rss,
                http.HTTPStatus.OK,
                content=self.get_rss_content("rss_high_num_episodes.xml"),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )

        with httpx.Client() as session:
            parse_feed(podcast, session)

        assert Episode.objects.count() == 4940

        podcast.refresh_from_db()

        assert podcast.rss
        assert podcast.active
        assert podcast.content_hash
        assert podcast.title == "Armstrong & Getty On Demand"

    def test_parse_ok_no_pub_date(self, mocker, db, categories):

        podcast = create_podcast(pub_date=None)

        # set pub date to before latest Fri, 19 Jun 2020 16:58:03 +0000

        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        create_episode(podcast=podcast, guid=episode_guid, title=episode_title)

        mock_client(
            mocker,
            mock_response(
                podcast.rss,
                http.HTTPStatus.OK,
                content=self.get_rss_content(),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )

        with httpx.Client() as session:
            parse_feed(podcast, session)

        # new episodes: 19
        assert Episode.objects.count() == 20

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.rss
        assert podcast.active
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

    def test_parse_same_content(self, mocker, db, categories):

        content = self.get_rss_content()
        podcast = create_podcast(content_hash=make_content_hash(content))

        mock_client(
            mocker,
            mock_response(
                podcast.rss,
                http.HTTPStatus.OK,
                content=content,
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )

        with httpx.Client() as session:
            with pytest.raises(NotModified):
                assert parse_feed(podcast, session)

        podcast.refresh_from_db()
        assert podcast.active
        assert podcast.modified is None
        assert podcast.parsed

    def test_parse_podcast_another_feed_same_content(self, mocker, podcast, categories):

        content = self.get_rss_content()

        create_podcast(content_hash=make_content_hash(content))

        mock_client(
            mocker,
            mock_response(
                podcast.rss,
                http.HTTPStatus.OK,
                content=content,
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )

        with httpx.Client() as session:
            with pytest.raises(Duplicate):
                assert parse_feed(podcast, session)

        podcast.refresh_from_db()

        assert not podcast.active
        assert podcast.modified is None
        assert podcast.parsed

    def test_parse_complete(self, mocker, podcast, categories):

        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        create_episode(podcast=podcast, guid=episode_guid, title=episode_title)

        mock_client(
            mocker,
            mock_response(
                podcast.rss,
                http.HTTPStatus.OK,
                content=self.get_rss_content("rss_mock_complete.xml"),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )

        with httpx.Client() as session:
            parse_feed(podcast, session)

        # new episodes: 19
        assert Episode.objects.count() == 20

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.rss
        assert not podcast.active
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

        mock_client(
            mocker,
            mock_response(
                self.redirect_rss,
                http.HTTPStatus.OK,
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
                content=self.get_rss_content(),
            ),
        )
        with httpx.Client() as session:
            parse_feed(podcast, session)
        assert Episode.objects.filter(podcast=podcast).count() == 20

        podcast.refresh_from_db()

        assert podcast.rss == self.redirect_rss
        assert podcast.active
        assert podcast.modified
        assert podcast.parsed

    def test_parse_permanent_redirect_url_taken(self, mocker, podcast, categories):
        other = create_podcast(rss=self.redirect_rss)
        current_rss = podcast.rss

        mock_client(
            mocker,
            mock_response(
                other.rss,
                http.HTTPStatus.OK,
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
                content=self.get_rss_content(),
            ),
        )

        with httpx.Client() as session:
            with pytest.raises(Duplicate):
                parse_feed(podcast, session)

        podcast.refresh_from_db()

        assert podcast.rss == current_rss
        assert not podcast.active
        assert podcast.parsed

    def test_parse_no_podcasts(self, mocker, podcast, categories):

        mock_client(
            mocker,
            mock_response(
                podcast.rss,
                http.HTTPStatus.OK,
                content=self.get_rss_content("rss_no_podcasts_mock.xml"),
            ),
        )

        with httpx.Client() as session:
            with pytest.raises(RssParserError):
                parse_feed(podcast, session)

        podcast.refresh_from_db()
        assert podcast.active
        assert podcast.parsed
        assert podcast.num_retries == 1

    def test_parse_no_podcasts_max_retries(self, mocker, podcast, categories):

        podcast.num_retries = 3

        mock_client(
            mocker,
            mock_response(
                podcast.rss,
                http.HTTPStatus.OK,
                content=self.get_rss_content("rss_no_podcasts_mock.xml"),
            ),
        )

        with httpx.Client() as session:

            with pytest.raises(RssParserError):
                parse_feed(podcast, session)

        podcast.refresh_from_db()
        assert not podcast.active
        assert podcast.parsed
        assert podcast.num_retries == 4

    def test_parse_empty_feed(self, mocker, podcast, categories):

        mock_client(
            mocker,
            mock_response(
                podcast.rss,
                http.HTTPStatus.OK,
                content=self.get_rss_content("rss_empty_mock.xml"),
            ),
        )

        with httpx.Client() as session:
            with pytest.raises(RssParserError):
                parse_feed(podcast, session)

        podcast.refresh_from_db()
        assert podcast.active
        assert podcast.parsed
        assert podcast.num_retries == 1

    def test_parse_not_modified(self, mocker, podcast, categories):

        podcast.num_retries = 1

        mock_client(mocker, mock_response(podcast.rss, http.HTTPStatus.NOT_MODIFIED))

        with httpx.Client() as session:
            with pytest.raises(NotModified):
                parse_feed(podcast, session)

        podcast.refresh_from_db()

        assert podcast.active
        assert podcast.modified is None
        assert podcast.parsed
        assert podcast.num_retries == 0

    def test_parse_http_gone(self, mocker, podcast, categories):

        mock_client(mocker, mock_response(podcast.rss, http.HTTPStatus.GONE))

        with httpx.Client() as session:
            with pytest.raises(Inaccessible):
                parse_feed(podcast, session)

        podcast.refresh_from_db()

        assert not podcast.active
        assert podcast.parsed

    def test_parse_http_server_error(self, mocker, podcast, categories):
        mock_client(
            mocker, mock_response(podcast.rss, http.HTTPStatus.INTERNAL_SERVER_ERROR)
        )

        with httpx.Client() as session:
            with pytest.raises(httpx.HTTPError):
                parse_feed(podcast, session)

        podcast.refresh_from_db()

        assert podcast.active
        assert podcast.parsed
        assert podcast.num_retries == 1

    def test_parse_http_server_error_max_retries(self, mocker, podcast, categories):
        podcast.num_retries = 3

        mock_client(
            mocker, mock_response(podcast.rss, http.HTTPStatus.INTERNAL_SERVER_ERROR)
        )

        with httpx.Client() as session:
            with pytest.raises(httpx.HTTPError):
                parse_feed(podcast, session)

        podcast.refresh_from_db()

        assert not podcast.active
        assert podcast.parsed
        assert podcast.num_retries == 4

    def test_parse_http_server_error_no_pub_date(self, mocker, podcast, categories):

        podcast.pub_date = None
        podcast.save()

        mock_client(
            mocker, mock_response(podcast.rss, http.HTTPStatus.INTERNAL_SERVER_ERROR)
        )

        with httpx.Client() as session:
            with pytest.raises(httpx.HTTPError):
                parse_feed(podcast, session)

        podcast.refresh_from_db()

        assert podcast.active
        assert podcast.parsed
