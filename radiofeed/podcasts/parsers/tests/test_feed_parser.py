import http
import pathlib
from datetime import datetime

import httpx
import pytest
from django.utils.text import slugify

from radiofeed.episodes.models import Episode
from radiofeed.episodes.tests.factories import EpisodeFactory
from radiofeed.http_client import Client
from radiofeed.podcasts.models import Category, Podcast
from radiofeed.podcasts.parsers.date_parser import parse_date
from radiofeed.podcasts.parsers.exceptions import (
    DatabaseOperationError,
    DiscontinuedError,
    DuplicateError,
    InvalidRSSError,
    NotModifiedError,
    PermanentHTTPError,
    TemporaryHTTPError,
)
from radiofeed.podcasts.parsers.feed_parser import get_categories_dict, parse_feed
from radiofeed.podcasts.parsers.rss_fetcher import make_content_hash
from radiofeed.podcasts.tests.factories import PodcastFactory


@pytest.fixture
def categories():
    get_categories_dict.cache_clear()
    return Category.objects.bulk_create(
        [
            Category(name=name, slug=slugify(name))
            for name in (
                "Medicine",
                "Philosophy",
                "Religion & Spirituality",
                "Science",
                "Society & Culture",
            )
        ],
        ignore_conflicts=True,
    )


def _mock_client(*, url="https://example.com", **response_kwargs):
    def _handle(request):
        request.url = url
        response = httpx.Response(**response_kwargs)
        response.request = request
        return response

    return Client(transport=httpx.MockTransport(_handle))


def _mock_error_client(exc):
    def _handle(request):
        raise exc

    return Client(transport=httpx.MockTransport(_handle))


def _get_mock_file_path(filename):
    return pathlib.Path(__file__).parent / "mocks" / filename


class TestFeedParser:
    mock_file = "rss_mock.xml"
    rss = "https://mysteriousuniverse.org/feed/podcast/"
    redirect_rss = "https://example.com/test.xml"
    updated = "Wed, 01 Jul 2020 15:25:26 +0000"

    def get_rss_content(self, filename=""):
        return _get_mock_file_path(filename or self.mock_file).read_bytes()

    @pytest.mark.django_db
    def test_parse_ok(self, categories):
        podcast = PodcastFactory(
            rss="https://mysteriousuniverse.org/feed/podcast/",
            pub_date=datetime(year=2020, month=3, day=1),
        )

        # set pub date to before latest Fri, 19 Jun 2020 16:58:03 +0000

        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        EpisodeFactory(podcast=podcast, guid=episode_guid, title=episode_title)

        # add episode to remove in update
        extra = EpisodeFactory(podcast=podcast)

        client = _mock_client(
            url=podcast.rss,
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content(),
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        parse_feed(podcast, client)

        # extra episode should be removed
        assert not podcast.episodes.filter(pk=extra.id).exists()

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.rss
        assert podcast.num_episodes == 20
        assert podcast.active is True
        assert podcast.content_hash
        assert podcast.feed_status == Podcast.FeedStatus.OK
        assert podcast.http_status == http.HTTPStatus.OK
        assert podcast.title == "Mysterious Universe"

        assert podcast.description == "Blog and Podcast specializing in offbeat news"
        assert podcast.owner == "8th Kind"

        tokens = set(podcast.extracted_text.split())

        assert tokens == {
            "socialsciences",
            "blog",
            "th",
            "society",
            "mu",
            "universe",
            "renner",
            "philosophy",
            "religionspirituality",
            "joshua",
            "science",
            "religion",
            "culture",
            "tooth",
            "kgb",
            "saber",
            "cop",
            "kind",
            "medicine",
            "timothy",
            "bruton",
            "tiger",
            "mysterious",
            "router",
            "king",
            "jim",
            "cutchin",
            "specializing",
            "societyculture",
            "sciencemedicine",
            "social",
            "spirituality",
            "offbeat",
            "tibetan",
            "zombie",
            "squid",
        }
        assert podcast.modified
        assert podcast.modified.day == 1
        assert podcast.modified.month == 7
        assert podcast.modified.year == 2020

        assert podcast.parsed

        assert podcast.etag
        assert podcast.explicit
        assert podcast.cover_url

        assert podcast.is_episodic()

        assert podcast.pub_date == parse_date("Fri, 19 Jun 2020 16:58:03 +0000")

        assigned_categories = [c.name for c in list(podcast.categories.all())]
        for name in (
            "Medicine",
            "Science",
            "Religion & Spirituality",
            "Society & Culture",
            "Philosophy",
        ):
            assert name in assigned_categories, f"Category {name} not assigned"

    @pytest.mark.django_db
    def test_parse_new_feed_url_same(self, categories):
        podcast = PodcastFactory(rss="https://feeds.simplecast.com/bgeVtxQX")

        client = _mock_client(
            url=podcast.rss,
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content("rss_new_feed_url.xml"),
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        parse_feed(podcast, client)

        podcast.refresh_from_db()

        assert podcast.feed_status == Podcast.FeedStatus.OK
        assert podcast.http_status == http.HTTPStatus.OK
        assert podcast.rss == "https://feeds.simplecast.com/bgeVtxQX"

    @pytest.mark.django_db
    def test_parse_new_feed_url_changed(self, categories):
        podcast = PodcastFactory()

        client = _mock_client(
            url=podcast.rss,
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content("rss_new_feed_url.xml"),
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        parse_feed(podcast, client)

        podcast.refresh_from_db()

        assert podcast.feed_status == Podcast.FeedStatus.OK
        assert podcast.http_status == http.HTTPStatus.OK
        assert podcast.rss == "https://feeds.simplecast.com/bgeVtxQX"

    @pytest.mark.django_db
    def test_parse_new_feed_url_other_podcast(self):
        podcast = PodcastFactory()
        other = PodcastFactory(rss="https://feeds.simplecast.com/bgeVtxQX")

        client = _mock_client(
            url=podcast.rss,
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content("rss_new_feed_url.xml"),
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        with pytest.raises(DuplicateError):
            parse_feed(podcast, client)

        podcast.refresh_from_db()

        assert podcast.feed_status == Podcast.FeedStatus.DUPLICATE
        assert podcast.http_status == http.HTTPStatus.OK
        assert podcast.active is False
        assert podcast.canonical == other

    @pytest.mark.django_db
    def test_parse_serial(self):
        podcast = PodcastFactory(
            rss="https://feeds.acast.com/public/shows/867a533e-5a8d-4e5c-81bc-f7e5a1fe29a5",
        )
        client = _mock_client(
            url=podcast.rss,
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content("rss_serial.xml"),
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        parse_feed(podcast, client)

        assert podcast.episodes.count() == 10

        podcast.refresh_from_db()

        assert podcast.rss
        assert podcast.active
        assert podcast.content_hash
        assert podcast.feed_status == Podcast.FeedStatus.OK
        assert podcast.http_status == http.HTTPStatus.OK

        assert podcast.is_serial()

    @pytest.mark.django_db
    def test_parse_links_as_ids(self):
        podcast = PodcastFactory(
            rss="https://feeds.feedburner.com/VarsoviaVentoPodkasto"
        )
        client = _mock_client(
            url=podcast.rss,
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content("rss_use_link_ids.xml"),
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        parse_feed(podcast, client)

        assert podcast.episodes.count() == 373

        podcast.refresh_from_db()

        assert podcast.rss
        assert podcast.active
        assert podcast.content_hash
        assert podcast.feed_status == Podcast.FeedStatus.OK
        assert podcast.http_status == http.HTTPStatus.OK
        assert podcast.title == "Varsovia Vento Podkasto"
        assert podcast.pub_date == parse_date("July 27, 2023 2:00+0000")

    @pytest.mark.django_db
    def test_parse_high_num_episodes(self, categories):
        podcast = PodcastFactory()
        client = _mock_client(
            url=podcast.rss,
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content("rss_high_num_episodes.xml"),
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        parse_feed(podcast, client)

        podcast.refresh_from_db()

        assert podcast.num_episodes == 4940
        assert podcast.rss
        assert podcast.active
        assert podcast.content_hash
        assert podcast.feed_status == Podcast.FeedStatus.OK
        assert podcast.http_status == http.HTTPStatus.OK
        assert podcast.title == "Armstrong & Getty On Demand"

    @pytest.mark.django_db
    def test_parse_ok_no_pub_date(self, categories):
        podcast = PodcastFactory(pub_date=None)

        # set pub date to before latest Fri, 19 Jun 2020 16:58:03 +0000

        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        EpisodeFactory(podcast=podcast, guid=episode_guid, title=episode_title)

        client = _mock_client(
            url=podcast.rss,
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content(),
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        parse_feed(podcast, client)

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        # new episodes: 19
        assert podcast.num_episodes == 20
        assert podcast.rss
        assert podcast.active
        assert podcast.content_hash
        assert podcast.feed_status == Podcast.FeedStatus.OK
        assert podcast.http_status == http.HTTPStatus.OK
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

        assigned_categories = [c.name for c in list(podcast.categories.all())]

        assert "Science" in assigned_categories
        assert "Religion & Spirituality" in assigned_categories
        assert "Society & Culture" in assigned_categories
        assert "Philosophy" in assigned_categories

    @pytest.mark.django_db
    def test_parse_same_content(self, mocker):
        content = self.get_rss_content()
        podcast = PodcastFactory(content_hash=make_content_hash(content))

        mock_parse_rss = mocker.patch("radiofeed.podcasts.parsers.rss_parser.parse_rss")

        client = _mock_client(
            status_code=http.HTTPStatus.OK,
            content=content,
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        with pytest.raises(NotModifiedError):
            parse_feed(podcast, client)

        podcast.refresh_from_db()

        assert podcast.active
        assert podcast.etag
        assert podcast.modified
        assert podcast.parsed
        assert podcast.http_status == http.HTTPStatus.OK

        mock_parse_rss.assert_not_called()

    @pytest.mark.django_db
    def test_parse_complete(self, podcast, categories):
        episode_guid = "https://mysteriousuniverse.org/?p=168097"
        episode_title = "original title"

        # test updated
        EpisodeFactory(podcast=podcast, guid=episode_guid, title=episode_title)

        client = _mock_client(
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content("rss_mock_complete.xml"),
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        parse_feed(podcast, client)

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.rss
        assert podcast.feed_status == Podcast.FeedStatus.DISCONTINUED
        assert podcast.http_status == http.HTTPStatus.OK
        assert podcast.num_episodes == 20
        assert podcast.active is False
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

    @pytest.mark.django_db
    def test_parse_permanent_redirect(self, podcast, categories):
        client = _mock_client(
            url=self.redirect_rss,
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content(),
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        parse_feed(podcast, client)

        podcast.refresh_from_db()

        assert podcast.num_episodes == 20
        assert podcast.feed_status == Podcast.FeedStatus.OK
        assert podcast.http_status == http.HTTPStatus.OK
        assert podcast.rss == self.redirect_rss
        assert podcast.active
        assert podcast.modified
        assert podcast.parsed

    @pytest.mark.django_db
    def test_parse_permanent_redirect_url_taken(self, podcast):
        other = PodcastFactory(rss=self.redirect_rss)
        current_rss = podcast.rss

        client = _mock_client(
            url=other.rss,
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content(),
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        with pytest.raises(DuplicateError):
            parse_feed(podcast, client)

        podcast.refresh_from_db()

        assert podcast.rss == current_rss
        assert not podcast.active
        assert podcast.parsed
        assert podcast.feed_status == Podcast.FeedStatus.DUPLICATE
        assert podcast.http_status == http.HTTPStatus.OK

        assert podcast.canonical == other

    @pytest.mark.django_db
    def test_parse_invalid_data(self, podcast):
        client = _mock_client(
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content("rss_invalid_data.xml"),
        )

        with pytest.raises(DatabaseOperationError):
            parse_feed(podcast, client)

        podcast.refresh_from_db()

        assert podcast.active is True
        assert podcast.parsed
        assert podcast.feed_status == Podcast.FeedStatus.DATABASE_ERROR
        assert podcast.http_status == http.HTTPStatus.OK

    @pytest.mark.django_db
    def test_parse_no_podcasts(self, podcast):
        client = _mock_client(
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content("rss_no_podcasts_mock.xml"),
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        with pytest.raises(InvalidRSSError):
            parse_feed(podcast, client)

        podcast.refresh_from_db()

        assert podcast.active is False
        assert podcast.feed_status == Podcast.FeedStatus.INVALID_RSS
        assert podcast.http_status == http.HTTPStatus.OK

        assert podcast.parsed

    @pytest.mark.django_db
    def test_parse_empty_feed(self, podcast):
        client = _mock_client(
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content("rss_empty_mock.xml"),
        )

        with pytest.raises(InvalidRSSError):
            parse_feed(podcast, client)

        podcast.refresh_from_db()

        assert podcast.active is False
        assert podcast.feed_status == Podcast.FeedStatus.INVALID_RSS
        assert podcast.http_status == http.HTTPStatus.OK
        assert podcast.parsed

    @pytest.mark.django_db
    def test_parse_not_modified(self, podcast):
        client = _mock_client(
            status_code=http.HTTPStatus.NOT_MODIFIED,
        )

        with pytest.raises(NotModifiedError):
            parse_feed(podcast, client)

        podcast.refresh_from_db()

        assert podcast.active
        assert podcast.feed_status == Podcast.FeedStatus.NOT_MODIFIED
        assert podcast.http_status == http.HTTPStatus.NOT_MODIFIED
        assert podcast.modified is None
        assert podcast.parsed

    @pytest.mark.django_db
    def test_parse_http_gone(self, podcast):
        client = _mock_client(
            status_code=http.HTTPStatus.GONE,
        )
        with pytest.raises(DiscontinuedError):
            parse_feed(podcast, client)

        podcast.refresh_from_db()

        assert podcast.active is False
        assert podcast.parsed
        assert podcast.feed_status == Podcast.FeedStatus.DISCONTINUED
        assert podcast.http_status == http.HTTPStatus.GONE

    @pytest.mark.django_db
    def test_parse_http_server_error(self, podcast):
        client = _mock_client(
            status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
        )

        with pytest.raises(TemporaryHTTPError):
            parse_feed(podcast, client)

        podcast.refresh_from_db()

        assert podcast.active is True
        assert podcast.parsed
        assert podcast.feed_status == Podcast.FeedStatus.TEMPORARY_HTTP_ERROR
        assert podcast.http_status == http.HTTPStatus.INTERNAL_SERVER_ERROR

    @pytest.mark.django_db
    def test_parse_http_not_found(self, podcast):
        client = _mock_client(
            status_code=http.HTTPStatus.NOT_FOUND,
        )

        with pytest.raises(PermanentHTTPError):
            parse_feed(podcast, client)

        podcast.refresh_from_db()

        assert podcast.active is False
        assert podcast.parsed
        assert podcast.feed_status == Podcast.FeedStatus.PERMANENT_HTTP_ERROR
        assert podcast.http_status == http.HTTPStatus.NOT_FOUND

    @pytest.mark.django_db
    def test_parse_connect_error(self, podcast):
        client = _mock_error_client(httpx.HTTPError("fail"))

        with pytest.raises(TemporaryHTTPError):
            parse_feed(podcast, client)

        podcast.refresh_from_db()

        assert podcast.active is True
        assert podcast.parsed
        assert podcast.feed_status == Podcast.FeedStatus.TEMPORARY_HTTP_ERROR
        assert podcast.http_status is None
