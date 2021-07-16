from __future__ import annotations

import http
import pathlib

import pytest
import requests

from django.utils import timezone

from audiotrails.episodes.factories import EpisodeFactory
from audiotrails.episodes.models import Episode
from audiotrails.podcasts.date_parser import parse_date
from audiotrails.podcasts.factories import CategoryFactory, PodcastFactory
from audiotrails.podcasts.feed_parser import (
    get_categories_dict,
    get_feed_headers,
    parse_feed,
)
from audiotrails.podcasts.models import Podcast


class MockResponse:
    def __init__(
        self,
        url: str,
        status: int = http.HTTPStatus.OK,
        content: bytes = b"",
        headers: None | dict = None,
    ):
        self.url = url
        self.content = content
        self.headers = headers or {}
        self.status_code = status

    def raise_for_status(self) -> None:
        ...


class BadMockResponse(MockResponse):
    def raise_for_status(self) -> None:
        raise requests.HTTPError()


class TestFeedHeaders:
    def test_has_etag(self):
        podcast = Podcast(etag="abc123")
        headers = get_feed_headers(podcast)
        assert headers["If-None-Match"] == f'"{podcast.etag}"'

    def test_is_modified(self):
        podcast = Podcast(modified=timezone.now())
        headers = get_feed_headers(podcast)
        assert headers["If-Modified-Since"]


class TestFeedParser:

    mock_file = "rss_mock.xml"
    mock_http_get = "requests.get"
    rss = "https://mysteriousuniverse.org/feed/podcast/"
    redirect_rss = "https://example.com/test.xml"
    updated = "Wed, 01 Jul 2020 15:25:26 +0000"

    @pytest.fixture
    def new_podcast(self, db):
        return PodcastFactory(cover_url=None, pub_date=None)

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

    def get_feedparser_content(self, filename: str = "") -> bytes:
        return open(
            pathlib.Path(__file__).parent / "mocks" / (filename or self.mock_file), "rb"
        ).read()

    def test_parse_no_podcasts(self, mocker, new_podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=new_podcast.rss,
                content=self.get_feedparser_content("rss_no_podcasts_mock.xml"),
            ),
        )
        episodes = parse_feed(new_podcast)
        assert len(episodes), 19

    def test_parse_empty_feed(self, mocker, new_podcast, categories):

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=new_podcast.rss,
                content=self.get_feedparser_content("rss_empty_mock.xml"),
            ),
        )
        episodes = parse_feed(new_podcast)
        assert len(episodes) == 0

    def test_parse_feed(self, mocker, new_podcast, categories):

        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        EpisodeFactory(podcast=new_podcast, guid=episode_guid, title=episode_title)

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=new_podcast.rss,
                content=self.get_feedparser_content(),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )
        episodes = parse_feed(new_podcast)

        # new episodes: 19
        assert len(episodes) == 19

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        new_podcast.refresh_from_db()

        assert new_podcast.rss
        assert new_podcast.title == "Mysterious Universe"

        assert (
            new_podcast.description
            == "Always interesting and often hilarious, join hosts Aaron Wright and Benjamin Grundy as they investigate the latest in futurology, weird science, consciousness research, alternative history, cryptozoology, UFOs, and new-age absurdity."
        )

        assert new_podcast.creators == "8th Kind"

        assert new_podcast.modified
        assert new_podcast.modified.day == 1
        assert new_podcast.modified.month == 7
        assert new_podcast.modified.year == 2020

        assert new_podcast.etag
        assert new_podcast.explicit
        assert new_podcast.cover_url

        assert new_podcast.pub_date == parse_date("Fri, 19 Jun 2020 16:58:03 +0000")
        assert new_podcast.num_episodes == 20

        assigned_categories = [c.name for c in new_podcast.categories.all()]

        assert "Science" in assigned_categories
        assert "Religion & Spirituality" in assigned_categories
        assert "Society & Culture" in assigned_categories
        assert "Philosophy" in assigned_categories

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
                content=self.get_feedparser_content(),
            ),
        )
        episodes = parse_feed(new_podcast)

        assert len(episodes) == 20

        new_podcast.refresh_from_db()

        assert new_podcast.rss == self.redirect_rss
        assert new_podcast.modified

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
                content=self.get_feedparser_content(),
            ),
        )
        episodes = parse_feed(new_podcast)

        assert len(episodes) == 0

        new_podcast.refresh_from_db()

        assert new_podcast.rss == current_rss
        assert not new_podcast.active
        assert new_podcast.redirect_to == other

    def test_parse_feed_not_modified(self, mocker, new_podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                new_podcast.rss, status=http.HTTPStatus.NOT_MODIFIED
            ),
        )
        episodes = parse_feed(new_podcast)

        assert episodes == []

        new_podcast.refresh_from_db()
        assert new_podcast.active
        assert not new_podcast.modified

    def test_parse_feed_error(self, mocker, new_podcast, categories):
        mocker.patch(self.mock_http_get, side_effect=requests.RequestException)
        episodes = parse_feed(new_podcast)

        assert episodes == []
        assert new_podcast.active
        assert new_podcast.exception

    def test_parse_feed_gone(self, mocker, new_podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(new_podcast.rss, status=http.HTTPStatus.GONE),
        )
        episodes = parse_feed(new_podcast)

        assert episodes == []

        new_podcast.refresh_from_db()

        assert not new_podcast.active
        assert not new_podcast.exception
        assert new_podcast.error_status == http.HTTPStatus.GONE
