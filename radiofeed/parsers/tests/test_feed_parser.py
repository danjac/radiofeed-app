import http
import pathlib
from datetime import datetime

import httpx
import pytest
from django.db.utils import DatabaseError
from django.utils.text import slugify

from radiofeed.client import Client
from radiofeed.episodes.models import Episode
from radiofeed.episodes.tests.factories import EpisodeFactory
from radiofeed.parsers.date_parser import parse_date
from radiofeed.parsers.feed_parser import get_categories_dict, parse_feed
from radiofeed.parsers.rss_fetcher import make_content_hash
from radiofeed.podcasts.models import Category, Podcast
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

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.SUCCESS

        # extra episode should be removed
        assert not podcast.episodes.filter(pk=extra.id).exists()

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.rss
        assert podcast.num_episodes == 20
        assert podcast.active is True
        assert podcast.content_hash
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

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.SUCCESS

        podcast.refresh_from_db()

        assert podcast.feed_status == result

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

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.SUCCESS

        podcast.refresh_from_db()

        assert podcast.feed_status == Podcast.FeedStatus.SUCCESS
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

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.DUPLICATE

        podcast.refresh_from_db()

        assert podcast.feed_status == result
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

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.SUCCESS

        assert podcast.episodes.count() == 10

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.rss
        assert podcast.active
        assert podcast.content_hash

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

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.SUCCESS

        assert podcast.episodes.count() == 373

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.rss
        assert podcast.active
        assert podcast.content_hash
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

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.SUCCESS

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.num_episodes == 4940
        assert podcast.rss
        assert podcast.active
        assert podcast.content_hash
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

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.SUCCESS

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        # new episodes: 19
        assert podcast.num_episodes == 20
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

        assigned_categories = [c.name for c in list(podcast.categories.all())]

        assert "Science" in assigned_categories
        assert "Religion & Spirituality" in assigned_categories
        assert "Society & Culture" in assigned_categories
        assert "Philosophy" in assigned_categories

    @pytest.mark.django_db
    def test_parse_same_content(self, mocker):
        content = self.get_rss_content()
        podcast = PodcastFactory(content_hash=make_content_hash(content))

        mock_parse_rss = mocker.patch("radiofeed.parsers.rss_parser.parse_rss")

        client = _mock_client(
            status_code=http.HTTPStatus.OK,
            content=content,
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.NOT_MODIFIED

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.active
        assert podcast.parsed

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

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.DISCONTINUED

        # check episode updated
        episode = Episode.objects.get(guid=episode_guid)
        assert episode.title != episode_title

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.rss
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

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.SUCCESS

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.num_episodes == 20
        assert podcast.rss == self.redirect_rss
        assert podcast.active
        assert podcast.modified
        assert podcast.parsed

    @pytest.mark.django_db
    def test_parse_permanent_redirect_url_taken(self, podcast, categories):
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

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.DUPLICATE

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.rss == current_rss
        assert not podcast.active
        assert podcast.parsed

        assert podcast.canonical == other

    @pytest.mark.django_db
    def test_parse_with_canonical_cycle(self, podcast, categories):
        """
        Test parse_feed when the canonical chain contains a cycle.
        Ensures ingestion does not hang and duplicate detection works.
        """

        # Create another podcast to form the cycle
        other = PodcastFactory()

        # Form the cycle: podcast -> other -> podcast
        podcast.canonical = other
        podcast.save(update_fields=["canonical"])
        other.canonical = podcast
        other.save(update_fields=["canonical"])

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

        # Run parse_feed normally
        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.DUPLICATE

        # Assert podcast was marked duplicate correctly
        podcast.refresh_from_db()
        assert podcast.feed_status == result
        assert podcast.rss == current_rss
        assert not podcast.active
        assert podcast.parsed

        # Deterministic canonical: should always be 'other' (the .first() in query)
        assert podcast.canonical == other

    @pytest.mark.django_db
    def test_parse_feed_duplicate_chain_bug(self, categories):
        """
        Test the original duplicate canonical bug scenario:
        - Podcast A is canonical
        - Podcast B is a duplicate pointing to A
        - Feed for A declares canonical URL = B
        Ensure A stays active, B stays inactive, DuplicateError is handled correctly.
        """

        # Create canonical podcast A
        podcast_a = PodcastFactory(active=True, canonical=None)
        original_rss = podcast_a.rss

        # Create duplicate podcast B pointing to A
        podcast_b = PodcastFactory(active=False, canonical=podcast_a)

        # Mock feed for Podcast A pointing to B's RSS
        client = _mock_client(
            url=podcast_b.rss,  # feed says canonical is B
            status_code=200,
            content=self.get_rss_content(),  # some valid RSS content
        )

        # Parse the feed
        result = parse_feed(podcast_a, client)
        assert result == Podcast.FeedStatus.SUCCESS

        # Reload from DB
        podcast_a.refresh_from_db()

        # Assertions

        # Podcast A stays active (canonical root)
        assert podcast_a.active
        assert podcast_a.rss == original_rss
        assert podcast_a.feed_status == Podcast.FeedStatus.SUCCESS

        # Result of parse_feed reflects that feed was ingested successfully
        assert result == Podcast.FeedStatus.SUCCESS

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

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.INVALID_RSS

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.active is True
        assert podcast.num_retries == 1
        assert podcast.parsed
        assert podcast.exception

    @pytest.mark.django_db
    def test_parse_no_podcasts_exceed_max_retries(self):
        podcast = PodcastFactory(num_retries=Podcast.MAX_RETRIES + 1)
        client = _mock_client(
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content("rss_no_podcasts_mock.xml"),
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.INVALID_RSS

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.active is False
        assert podcast.num_retries == Podcast.MAX_RETRIES + 2
        assert podcast.parsed
        assert podcast.exception

    @pytest.mark.django_db
    def test_parse_empty_feed(self, podcast):
        client = _mock_client(
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content("rss_empty_mock.xml"),
        )

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.INVALID_RSS

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.active is True
        assert podcast.num_retries == 1
        assert podcast.parsed
        assert podcast.exception

    @pytest.mark.django_db
    def test_parse_not_modified(self, podcast):
        client = _mock_client(status_code=http.HTTPStatus.NOT_MODIFIED)

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.NOT_MODIFIED

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.active
        assert podcast.modified is None
        assert podcast.parsed

    @pytest.mark.django_db
    def test_parse_http_gone(self, podcast):
        client = _mock_client(status_code=http.HTTPStatus.GONE)

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.DISCONTINUED

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.active is False
        assert podcast.parsed

    @pytest.mark.django_db
    def test_parse_http_server_error(self, podcast):
        client = _mock_client(status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR)

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.UNAVAILABLE

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.active is True
        assert podcast.num_retries == 1
        assert podcast.parsed
        assert podcast.exception

    @pytest.mark.django_db
    def test_parse_http_not_found(self, podcast):
        client = _mock_client(status_code=http.HTTPStatus.NOT_FOUND)

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.UNAVAILABLE

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.active is True
        assert podcast.num_retries == 1
        assert podcast.parsed
        assert podcast.exception

    @pytest.mark.django_db
    def test_parse_http_not_found_exceed_num_retries(self):
        podcast = PodcastFactory(num_retries=Podcast.MAX_RETRIES + 1)

        client = _mock_client(
            status_code=http.HTTPStatus.NOT_FOUND,
        )

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.UNAVAILABLE

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.active is False
        assert podcast.num_retries == Podcast.MAX_RETRIES + 2
        assert podcast.parsed
        assert podcast.exception

    @pytest.mark.django_db
    def test_parse_connect_error(self, podcast):
        client = _mock_error_client(httpx.HTTPError("fail"))

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.UNAVAILABLE

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.active is True
        assert podcast.parsed
        assert podcast.exception

    @pytest.mark.django_db
    def test_other_error(self, podcast, mocker):
        mocker.patch("django.db.transaction.atomic", side_effect=DatabaseError("fail"))

        client = _mock_client(
            url=podcast.rss,
            status_code=http.HTTPStatus.OK,
            content=self.get_rss_content(),
            headers={
                "ETag": "abc123",
                "Last-Modified": self.updated,
            },
        )

        result = parse_feed(podcast, client)
        assert result == Podcast.FeedStatus.DATABASE_ERROR

        podcast.refresh_from_db()

        assert podcast.feed_status == result

        assert podcast.active is True
        assert podcast.parsed
        assert "fail" in podcast.exception
