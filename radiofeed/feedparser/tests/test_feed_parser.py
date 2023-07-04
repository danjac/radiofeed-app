import dataclasses
import http
import pathlib
from datetime import datetime

import pytest
import requests
from django.utils import timezone

from radiofeed.episodes.models import Episode
from radiofeed.episodes.tests.factories import create_episode
from radiofeed.feedparser.date_parser import parse_date
from radiofeed.feedparser.exceptions import (
    DuplicateError,
    InaccessibleError,
    InvalidRSSError,
    NotModifiedError,
    UnavailableError,
)
from radiofeed.feedparser.feed_parser import (
    FeedParser,
    get_categories,
    make_content_hash,
)
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import create_category, create_podcast


@dataclasses.dataclass
class MockResponse:
    url: str
    status_code: int
    content: bytes = b""
    headers: dict | None = None
    exception: Exception | None = None
    links: dict = dataclasses.field(default_factory=dict)

    def raise_for_status(self):
        if self.exception:
            raise self.exception


class TestFeedParser:
    mock_file = "rss_mock.xml"
    rss = "https://mysteriousuniverse.org/feed/podcast/"
    redirect_rss = "https://example.com/test.xml"
    updated = "Wed, 01 Jul 2020 15:25:26 +0000"

    @pytest.fixture()
    def categories(self):
        get_categories.cache_clear()

        return [
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

    @pytest.mark.django_db()
    def test_parse_unhandled_exception(self, podcast, mocker):
        mocker.patch(
            "radiofeed.feedparser.feed_parser.FeedParser.parse",
            side_effect=ValueError("oops"),
        )

        with pytest.raises(ValueError, match="oops"):
            FeedParser(podcast).parse()

        podcast.refresh_from_db()
        assert podcast.active

    @pytest.mark.django_db()
    def test_parse_ok(self, mocker, categories):
        # set date to before latest

        podcast = create_podcast(
            rss="https://mysteriousuniverse.org/feed/podcast/",
            pub_date=datetime(year=2020, month=3, day=1),
            num_retries=3,
        )

        # set pub date to before latest Fri, 19 Jun 2020 16:58:03 +0000

        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        create_episode(podcast=podcast, guid=episode_guid, title=episode_title)

        # add episode to remove in update
        extra = create_episode(podcast=podcast)

        mocker.patch(
            "requests.get",
            return_value=MockResponse(
                url=podcast.rss,
                status_code=http.HTTPStatus.OK,
                content=self.get_rss_content(),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )

        FeedParser(podcast).parse()

        # new episodes: 19
        assert podcast.episodes.count() == 20

        # extra episode should be removed
        assert not podcast.episodes.filter(pk=extra.id).exists()

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.rss
        assert podcast.parser_error is None
        assert podcast.active
        assert podcast.num_retries == 0
        assert podcast.content_hash
        assert podcast.title == "Mysterious Universe"

        assert podcast.description == "Blog and Podcast specializing in offbeat news"
        assert podcast.owner == "8th Kind"

        assert (
            podcast.extracted_text
            == "mysterious universe blog specializing offbeat th kind science medicine science social science religion spirituality spirituality society culture philosophy mu tibetan zombie mu saber tooth tiger king mu kgb cop mu joshua cutchin timothy renner mu squid router mu jim bruton"  # noqa
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

    @pytest.mark.django_db()
    def test_parse_high_num_episodes(self, mocker, categories):
        podcast = create_podcast()

        mocker.patch(
            "requests.get",
            return_value=MockResponse(
                url=podcast.rss,
                status_code=http.HTTPStatus.OK,
                content=self.get_rss_content("rss_high_num_episodes.xml"),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )

        FeedParser(podcast).parse()

        assert Episode.objects.count() == 4940

        podcast.refresh_from_db()

        assert podcast.parser_error is None
        assert podcast.rss
        assert podcast.active
        assert podcast.content_hash
        assert podcast.title == "Armstrong & Getty On Demand"

    @pytest.mark.django_db()
    def test_parse_ok_no_pub_date(self, mocker, categories):
        podcast = create_podcast(pub_date=None)

        # set pub date to before latest Fri, 19 Jun 2020 16:58:03 +0000

        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        create_episode(podcast=podcast, guid=episode_guid, title=episode_title)

        mocker.patch(
            "requests.get",
            return_value=MockResponse(
                url=podcast.rss,
                status_code=http.HTTPStatus.OK,
                content=self.get_rss_content(),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )

        FeedParser(podcast).parse()

        # new episodes: 19
        assert Episode.objects.count() == 20

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.parser_error is None
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

    @pytest.mark.django_db()
    def test_parse_same_content(self, mocker, categories):
        content = self.get_rss_content()
        podcast = create_podcast(content_hash=make_content_hash(content))

        mocker.patch(
            "requests.get",
            return_value=MockResponse(
                url=podcast.rss,
                status_code=http.HTTPStatus.OK,
                content=content,
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )

        with pytest.raises(NotModifiedError):
            FeedParser(podcast).parse()

        podcast.refresh_from_db()

        assert podcast.parser_error == Podcast.ParserError.NOT_MODIFIED

        assert podcast.active
        assert podcast.modified is None
        assert podcast.parsed

    @pytest.mark.django_db()
    def test_parse_podcast_another_feed_same_content(self, mocker, podcast, categories):
        content = self.get_rss_content()

        create_podcast(content_hash=make_content_hash(content))

        mocker.patch(
            "requests.get",
            return_value=MockResponse(
                url=podcast.rss,
                status_code=http.HTTPStatus.OK,
                content=content,
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )

        with pytest.raises(DuplicateError):
            FeedParser(podcast).parse()

        podcast.refresh_from_db()

        assert podcast.parser_error == Podcast.ParserError.DUPLICATE

        assert podcast.active is False
        assert podcast.modified is None
        assert podcast.parsed

    @pytest.mark.django_db()
    def test_parse_complete(self, mocker, podcast, categories):
        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        create_episode(podcast=podcast, guid=episode_guid, title=episode_title)

        mocker.patch(
            "requests.get",
            return_value=MockResponse(
                url=podcast.rss,
                status_code=http.HTTPStatus.OK,
                content=self.get_rss_content("rss_mock_complete.xml"),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )

        FeedParser(podcast).parse()

        # new episodes: 19
        assert Episode.objects.count() == 20

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.rss
        assert podcast.active is False
        assert podcast.parser_error is None
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

    @pytest.mark.django_db()
    def test_parse_permanent_redirect(self, mocker, podcast, categories):
        mocker.patch(
            "requests.get",
            return_value=MockResponse(
                url=self.redirect_rss,
                status_code=http.HTTPStatus.OK,
                content=self.get_rss_content(),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )

        FeedParser(podcast).parse()
        assert Episode.objects.filter(podcast=podcast).count() == 20

        podcast.refresh_from_db()

        assert podcast.parser_error is None

        assert podcast.rss == self.redirect_rss
        assert podcast.active
        assert podcast.modified
        assert podcast.parsed

    @pytest.mark.django_db()
    def test_parse_permanent_redirect_url_taken(self, mocker, podcast, categories):
        other = create_podcast(rss=self.redirect_rss)
        current_rss = podcast.rss

        mocker.patch(
            "requests.get",
            return_value=MockResponse(
                url=other.rss,
                status_code=http.HTTPStatus.OK,
                content=self.get_rss_content(),
                headers={
                    "ETag": "abc123",
                    "Last-Modified": self.updated,
                },
            ),
        )

        with pytest.raises(DuplicateError):
            FeedParser(podcast).parse()

        podcast.refresh_from_db()

        assert podcast.rss == current_rss
        assert not podcast.active
        assert podcast.parsed

    @pytest.mark.django_db()
    def test_parse_no_podcasts(self, mocker, podcast, categories):
        mocker.patch(
            "requests.get",
            return_value=MockResponse(
                url=podcast.rss,
                status_code=http.HTTPStatus.OK,
                content=self.get_rss_content("rss_no_podcasts_mock.xml"),
            ),
        )

        with pytest.raises(InvalidRSSError):
            FeedParser(podcast).parse()

        podcast.refresh_from_db()

        assert podcast.parser_error == Podcast.ParserError.INVALID_RSS

        assert podcast.active
        assert podcast.parsed
        assert podcast.num_retries == 1

    @pytest.mark.django_db()
    def test_parse_no_podcasts_max_retries(self, mocker, podcast, categories):
        podcast.num_retries = 3

        mocker.patch(
            "requests.get",
            return_value=MockResponse(
                url=podcast.rss,
                status_code=http.HTTPStatus.OK,
                content=self.get_rss_content("rss_no_podcasts_mock.xml"),
            ),
        )

        with pytest.raises(InvalidRSSError):
            FeedParser(podcast).parse()

        podcast.refresh_from_db()

        assert podcast.parser_error == Podcast.ParserError.INVALID_RSS

        assert podcast.active is False
        assert podcast.parsed
        assert podcast.num_retries == 4

    @pytest.mark.django_db()
    def test_parse_empty_feed(self, mocker, podcast, categories):
        mocker.patch(
            "requests.get",
            return_value=MockResponse(
                url=podcast.rss,
                status_code=http.HTTPStatus.OK,
                content=self.get_rss_content("rss_empty_mock.xml"),
            ),
        )

        with pytest.raises(InvalidRSSError):
            FeedParser(podcast).parse()

        podcast.refresh_from_db()

        assert podcast.parser_error == Podcast.ParserError.INVALID_RSS

        assert podcast.active
        assert podcast.parsed
        assert podcast.num_retries == 1

    @pytest.mark.django_db()
    def test_parse_not_modified(self, mocker, podcast, categories):
        podcast.num_retries = 1

        mocker.patch(
            "requests.get",
            return_value=MockResponse(
                url=podcast.rss, status_code=http.HTTPStatus.NOT_MODIFIED
            ),
        )

        with pytest.raises(NotModifiedError):
            FeedParser(podcast).parse()

        podcast.refresh_from_db()

        assert podcast.parser_error == Podcast.ParserError.NOT_MODIFIED

        assert podcast.active
        assert podcast.modified is None
        assert podcast.parsed
        assert podcast.num_retries == 0

    @pytest.mark.django_db()
    def test_parse_http_gone(self, mocker, podcast, categories):
        mocker.patch(
            "requests.get",
            return_value=MockResponse(
                url=podcast.rss, status_code=http.HTTPStatus.GONE
            ),
        )

        with pytest.raises(InaccessibleError):
            FeedParser(podcast).parse()

        podcast.refresh_from_db()

        assert podcast.parser_error == Podcast.ParserError.INACCESSIBLE

        assert not podcast.active
        assert podcast.parsed

    @pytest.mark.django_db()
    def test_parse_connect_error(self, mocker, podcast, categories):
        mocker.patch("requests.get", side_effect=requests.ConnectionError("fail"))

        with pytest.raises(UnavailableError):
            FeedParser(podcast).parse()

        podcast.refresh_from_db()

        assert podcast.parser_error == Podcast.ParserError.UNAVAILABLE

        assert podcast.active
        assert podcast.parsed
        assert podcast.num_retries == 1

    @pytest.mark.django_db()
    def test_parse_connect_max_retries(self, mocker, podcast, categories):
        podcast.num_retries = 3

        mocker.patch("requests.get", side_effect=requests.ConnectionError("fail"))

        with pytest.raises(UnavailableError):
            FeedParser(podcast).parse()

        podcast.refresh_from_db()

        assert podcast.parser_error == Podcast.ParserError.UNAVAILABLE

        assert podcast.active is False
        assert podcast.parsed
        assert podcast.num_retries == 4
