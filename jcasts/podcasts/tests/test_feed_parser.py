from __future__ import annotations

import http
import json
import pathlib

from datetime import datetime, timedelta

import pytest
import pytz
import requests

from django.utils import timezone
from pydantic import ValidationError

from jcasts.episodes.factories import EpisodeFactory
from jcasts.episodes.models import Episode
from jcasts.podcasts.date_parser import parse_date
from jcasts.podcasts.factories import CategoryFactory, PodcastFactory
from jcasts.podcasts.feed_parser import (
    FeedItem,
    Link,
    get_categories_dict,
    get_feed_headers,
    parse_feed,
    parse_podcast_feeds,
)
from jcasts.podcasts.models import Podcast


class MockResponse:
    def __init__(
        self,
        url: str = "",
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


class TestParsePodcastFeeds:
    @pytest.mark.parametrize(
        "force_update,active,scheduled,limit,result",
        [
            (False, True, timedelta(hours=-1), 1000, 1),
            (False, True, timedelta(hours=-1), None, 1),
            (False, True, timedelta(hours=1), 1000, 0),
            (True, True, timedelta(hours=1), 1000, 1),
            (True, True, None, 1000, 1),
            (True, False, None, 1000, 0),
            (False, False, None, 1000, 0),
        ],
    )
    def test_parse_podcast_feeds(
        self,
        db,
        mocker,
        force_update,
        active,
        scheduled,
        limit,
        result,
    ):

        mock_parse_feed = mocker.patch("jcasts.podcasts.feed_parser.parse_feed.delay")

        now = timezone.now()
        PodcastFactory(
            active=active,
            scheduled=now + scheduled if scheduled else None,
        )
        assert parse_podcast_feeds(force_update=force_update, limit=limit) == result

        if result:
            mock_parse_feed.assert_called()
        else:
            mock_parse_feed.assert_not_called()


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

        result = parse_feed(new_podcast.rss)
        assert not result
        with pytest.raises(ValidationError):
            result.raise_exception()

        new_podcast.refresh_from_db()
        assert new_podcast.active
        assert new_podcast.parsed

    def test_parse_empty_feed(self, mocker, new_podcast, categories):

        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(
                url=new_podcast.rss,
                content=self.get_feedparser_content("rss_empty_mock.xml"),
            ),
        )

        result = parse_feed(new_podcast.rss)
        assert not result
        with pytest.raises(ValidationError):
            result.raise_exception()

        new_podcast.refresh_from_db()
        assert new_podcast.active
        assert new_podcast.parsed

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
                content=self.get_feedparser_content(),
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
            new_podcast.description
            == "Always interesting and often hilarious, join hosts Aaron Wright and Benjamin Grundy as they investigate the latest in futurology, weird science, consciousness research, alternative history, cryptozoology, UFOs, and new-age absurdity."
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
        assert parse_feed(new_podcast.rss)
        assert Episode.objects.filter(podcast=new_podcast).count() == 20

        new_podcast.refresh_from_db()

        assert new_podcast.rss == self.redirect_rss
        assert new_podcast.modified
        assert new_podcast.parsed

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
        assert not parse_feed(new_podcast.rss)

        new_podcast.refresh_from_db()

        assert new_podcast.rss == current_rss
        assert not new_podcast.active
        assert new_podcast.scheduled is None
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
        assert not new_podcast.modified

    def test_parse_feed_error(self, mocker, new_podcast, categories):
        mocker.patch(self.mock_http_get, side_effect=requests.RequestException)

        result = parse_feed(new_podcast.rss)
        assert result.success is False

        with pytest.raises(requests.RequestException):
            result.raise_exception()

        new_podcast.refresh_from_db()
        assert new_podcast.active

    def test_parse_feed_gone(self, mocker, new_podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(new_podcast.rss, status=http.HTTPStatus.GONE),
        )
        result = parse_feed(new_podcast.rss)
        assert result.success is False

        # no exception
        result.raise_exception()

        new_podcast.refresh_from_db()

        assert not new_podcast.active
        assert new_podcast.scheduled is None


class TestLinkModel:
    def test_is_not_audio(self):
        link = Link(
            **{
                "rel": "alternate",
                "type": "text/html",
                "href": "https://play.acast.com/s/dansnowshistoryhit/theoriginsofenglish",
            },
        )
        assert link.is_audio() is False

    def test_is_audio(self):
        link = Link(
            **{
                "length": "55705268",
                "type": "audio/mpeg",
                "href": "https://sphinx.acast.com/channelhistoryhit/dansnowshistoryhit/theoriginsofenglish/media.mp3",
                "rel": "enclosure",
            }
        )

        assert link.is_audio() is True


class TestFeedItemModel:
    @pytest.fixture
    def item_data(self):
        return json.load(
            open(pathlib.Path(__file__).parent / "mocks" / "feed_item.json", "rb")
        )

    def test_missing_audio(self, item_data):
        del item_data["links"]
        with pytest.raises(ValidationError):
            FeedItem.parse_obj(item_data)

    def test_invalid_audio(self, item_data):
        item_data["links"] = [
            {
                "length": "55705268",
                "rel": "enclosure",
                "type": "audio/mpeg",
            },
        ]
        with pytest.raises(ValidationError):
            FeedItem.parse_obj(item_data)

    def test_published(self, item_data):
        del item_data["published"]
        with pytest.raises(ValidationError):
            FeedItem.parse_obj(item_data)

    def test_published_in_future(self, item_data):
        item_data["published"] = (timezone.now() + timedelta(days=1)).strftime(
            "%a, %d %b %Y %H:%M:%s"
        )
        with pytest.raises(ValidationError):
            FeedItem.parse_obj(item_data)

    def test_missing_content(self, item_data):
        del item_data["content"]
        item = FeedItem.parse_obj(item_data)
        assert item.description == ""

    def test_parse_complete_item(self, item_data):
        item = FeedItem.parse_obj(item_data)

        assert item.id == "74561fff-4b98-4985-a36f-4970be28782e"
        assert item.title == "The Origins of English"
        assert item.published == datetime(2021, 8, 7, 4, 0, tzinfo=pytz.timezone("GMT"))

        assert item.itunes_duration == "00:38:34"
        assert item.itunes_episodetype == "full"
        assert item.itunes_explicit is False

        assert (
            item.link
            == "https://play.acast.com/s/dansnowshistoryhit/theoriginsofenglish"
        )

        assert item.image.href == (
            "https://thumborcdn.acast.com/AA9YH364rPs8gxGOwgyXGEvLhyo=/3000x3000/https://mediacdn.acast.com/assets/74561fff-4b98-4985-a36f-4970be28782e/cover-image-ks08c9r7-gonemedieval_square_3000x3000.jpg"
        )

        assert item.audio.href == (
            "https://sphinx.acast.com/channelhistoryhit/dansnowshistoryhit/theoriginsofenglish/media.mp3"
        )
        assert item.audio.length == 55705268
        assert item.audio.rel == "enclosure"
        assert item.audio.type == "audio/mpeg"

        assert item.summary == (
            "Approximately 1.35 billion people use it, either as a first or "
            "second language, so English and the way that we speak it has a "
            "daily impact on huge numbers of people. But how did the English "
            "language develop? In this episode from our sibling podcast Gone "
            "Medieval, Cat Jarman spoke to Eleanor Rye, an Associate Lecturer "
            "in English Language and Linguistics at the University of York. "
            "Using the present-day language, place names and dialects as "
            "evidence, Ellie shows us how English was impacted by a series of "
            "migrations.&nbsp;&nbsp; &#10;&nbsp;<br /><hr /><p>See <a "
            'href="https://acast.com/privacy" rel="noopener noreferrer" '
            'style="color: grey;" target="_blank">acast.com/privacy</a> for '
            "privacy and opt-out information.</p>"
        )

        assert item.description == (
            "<p>Approximately 1.35 billion people use it, either as "
            "a first or second language, so English and the way "
            "that we speak it has a daily impact on huge numbers of "
            "people. But how did the English language develop? In "
            "this episode from our sibling podcast <a "
            'href="https://podfollow.com/gone-medieval/view" '
            'rel="noopener noreferrer" target="_blank">Gone '
            "Medieval</a>, Cat Jarman spoke to Eleanor Rye, an "
            "Associate Lecturer in English Language and Linguistics "
            "at the University of York. Using the present-day "
            "language, place names and dialects as evidence, Ellie "
            "shows us how English was impacted by a series of "
            "migrations.&nbsp;&nbsp;</p> &#10;&nbsp;<br /><hr "
            '/><p>See <a href="https://acast.com/privacy" '
            'rel="noopener noreferrer" style="color: grey;" '
            'target="_blank">acast.com/privacy</a> for privacy and '
            "opt-out information.</p>"
        )
