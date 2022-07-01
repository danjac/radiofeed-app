import datetime
import http
import pathlib

from datetime import timedelta

import pytest
import requests

from django.utils import timezone

from radiofeed.common.utils.dates import parse_date
from radiofeed.episodes.factories import EpisodeFactory
from radiofeed.episodes.models import Episode
from radiofeed.podcasts.factories import CategoryFactory, PodcastFactory
from radiofeed.podcasts.feed_parser import converters, parse_feed, validators
from radiofeed.podcasts.feed_parser.feed_parser import (
    FeedParser,
    get_categories_dict,
    make_content_hash,
)
from radiofeed.podcasts.feed_parser.models import Feed, Item
from radiofeed.podcasts.feed_parser.rss_parser import RssParserError, parse_rss
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

    def test_has_etag(self):
        podcast = Podcast(etag="abc123")
        headers = FeedParser(podcast).get_feed_headers()
        assert headers["If-None-Match"] == f'"{podcast.etag}"'

    def test_is_modified(self):
        podcast = Podcast(modified=timezone.now())
        headers = FeedParser(podcast).get_feed_headers()
        assert headers["If-Modified-Since"]

    def get_rss_content(self, filename=""):
        return (
            pathlib.Path(__file__).parent / "mocks" / (filename or self.mock_file)
        ).read_bytes()

    def test_parse_unhandled_exception(self, podcast, mocker):

        mocker.patch(
            "radiofeed.podcasts.feed_parser.FeedParser.parse_rss",
            side_effect=ValueError,
        )
        with pytest.raises(ValueError):
            parse_feed(podcast)

    def test_parse_ok(self, db, mocker, categories):

        # set date to before latest
        podcast = PodcastFactory(pub_date=datetime.datetime(year=2020, month=3, day=1))

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
        assert podcast.content_hash
        assert podcast.title == "Mysterious Universe"

        assert podcast.description == "Blog and Podcast specializing in offbeat news"
        assert podcast.owner == "8th Kind"

        assert (
            podcast.extracted_text
            == "mysterious universe blog specializing offbeat th kind science social science religion spirituality spirituality society culture philosophy mu tibetan zombie mu saber tooth tiger king mu kgb cop mu joshua cutchin timothy renner mu squid router mu jim bruton"
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
        assert not podcast.active
        assert podcast.parsed

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
        assert not podcast.active
        assert podcast.parsed

    def test_parse_not_modified(self, mocker, podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=MockResponse(podcast.rss, status=http.HTTPStatus.NOT_MODIFIED),
        )
        assert not parse_feed(podcast)

        podcast.refresh_from_db()
        assert podcast.active
        assert podcast.modified is None
        assert podcast.parsed

    def test_parse_http_gone(self, mocker, podcast, categories):
        mocker.patch(
            self.mock_http_get,
            return_value=BadMockResponse(status=http.HTTPStatus.GONE),
        )
        assert not parse_feed(podcast)

        podcast.refresh_from_db()

        assert not podcast.active
        assert podcast.http_status == http.HTTPStatus.GONE
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
        assert podcast.parsed

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
        assert podcast.parsed


class TestExplicit:
    def test_true(self):
        assert converters.explicit("yes") is True

    def test_false(self):
        assert converters.explicit("no") is False

    def test_none(self):
        assert converters.explicit(None) is False


class TestUrlOrNone:
    def test_ok(self):
        assert (
            converters.url_or_none("http://yhanewashington.wixsite.com/1972")
            == "http://yhanewashington.wixsite.com/1972"
        )

    def test_bad_url(self):
        assert converters.url_or_none("yhanewashington.wixsite.com/1972") is None

    def test_none(self):
        assert converters.url_or_none(None) is None


class TestDuration:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, ""),
            ("", ""),
            ("invalid", ""),
            ("300", "300"),
            ("10:30", "10:30"),
            ("10:30:59", "10:30:59"),
            ("10:30:99", "10:30"),
        ],
    )
    def test_parse_duration(self, value, expected):
        assert converters.duration(value) == expected


class TestNotEmpty:
    @pytest.mark.parametrize(
        "value,raises",
        [
            ("ok", False),
            ("", True),
            (None, True),
        ],
    )
    def test_required(self, value, raises):

        if raises:
            with pytest.raises(ValueError):
                validators.required(None, None, value)
        else:
            validators.required(None, None, value)


class TestUrl:
    @pytest.mark.parametrize(
        "value,raises",
        [
            ("http://example.com", False),
            ("https://example.com", False),
            ("example", True),
        ],
    )
    def test_url(self, value, raises):
        if raises:
            with pytest.raises(ValueError):
                validators.url(None, None, value)
        else:
            validators.url(None, None, value)


class TestItem:
    def test_pub_date_none(self):
        with pytest.raises(ValueError):
            Item(
                guid="test",
                title="test",
                media_url="https://example.com/",
                media_type="audio/mpeg",
                pub_date=None,
            )

    def test_pub_date_in_future(self):
        with pytest.raises(ValueError):
            Item(
                guid="test",
                title="test",
                media_url="https://example.com/",
                media_type="audio/mpeg",
                pub_date=timezone.now() + timedelta(days=1),
            )

    def test_not_audio_mimetype(self):
        with pytest.raises(ValueError):
            Item(
                guid="test",
                title="test",
                media_url="https://example.com/",
                media_type="video/mpeg",
                pub_date=timezone.now() - timedelta(days=1),
            )

    def test_defaults(self):
        item = Item(
            guid="test",
            title="test",
            media_url="https://example.com/",
            media_type="audio/mpeg",
            pub_date=timezone.now() - timedelta(days=1),
        )

        assert item.explicit is False
        assert item.episode_type == "full"


class TestFeed:
    @pytest.fixture
    def item(self):
        return Item(
            guid="test",
            title="test",
            media_url="https://example.com/",
            media_type="audio/mpeg",
            pub_date=timezone.now() - timedelta(days=1),
        )

    def test_language(self, item):
        feed = Feed(
            title="test",
            language="fr-CA",
            items=[item],
        )
        assert feed.language == "fr"

    def test_no_items(self):
        with pytest.raises(ValueError):
            Feed(
                title="test",
                items=[],
            )

    def test_not_complete(self, item):
        feed = Feed(
            title="test",
            items=[item],
            complete="no",
        )

        assert feed.complete is False

    def test_complete(self, item):
        feed = Feed(
            title="test",
            items=[item],
            complete="yes",
        )

        assert feed.complete is True

    def test_defaults(self, item):
        feed = Feed(
            title="test",
            items=[item],
        )

        assert feed.complete is False
        assert feed.explicit is False
        assert feed.language == "en"
        assert feed.description == ""
        assert feed.categories == []
        assert feed.pub_date == item.pub_date


class TestParseRss:
    def read_mock_file(self, mock_filename):
        return (pathlib.Path(__file__).parent / "mocks" / mock_filename).read_bytes()

    def test_empty(self):
        with pytest.raises(RssParserError):
            parse_rss(b"")

    def test_invalid_xml(self):
        with pytest.raises(RssParserError):
            parse_rss(b"junk string")

    def test_missing_channel(self):
        with pytest.raises(RssParserError):
            parse_rss(b"<rss />")

    def test_invalid_feed_channel(self):
        with pytest.raises(RssParserError):
            parse_rss(b"<rss><channel /></rss>")

    def test_with_bad_chars(self):
        content = self.read_mock_file("rss_mock.xml").decode("utf-8")
        content = content.replace("&amp;", "&")
        feed = parse_rss(bytes(content.encode("utf-8")))

        assert len(feed.items) == 20
        assert feed.title == "Mysterious Universe"

    @pytest.mark.parametrize(
        "filename,title,num_items",
        [
            ("rss_missing_enc_length.xml", "The Vanilla JS Podcast", 71),
            (
                "rss_bad_urls.xml",
                "1972",
                3,
            ),
            (
                "rss_bad_pub_date.xml",
                "Old Time Radio Mystery Theater",
                69,
            ),
            (
                "rss_mock_large.xml",
                "AAA United Public Radio & UFO Paranormal Radio Network",
                8641,
            ),
            ("rss_mock_iso_8859-1.xml", "Thunder & Lightning", 643),
            (
                "rss_mock_small.xml",
                "ABC News Update",
                1,
            ),
            (
                "rss_mock.xml",
                "Mysterious Universe",
                20,
            ),
            ("rss_invalid_duration.xml", "At The Races with Steve Byk", 450),
            (
                "rss_bad_cover_urls.xml",
                "TED Talks Daily",
                327,
            ),
            (
                "rss_superfeedr.xml",
                "The Chuck ToddCast: Meet the Press",
                296,
            ),
        ],
    )
    def test_parse_rss(self, filename, title, num_items):
        feed = parse_rss(self.read_mock_file(filename))
        assert feed.title == title
        assert len(feed.items) == num_items
