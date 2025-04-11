import pytest
from django.utils import timezone

from radiofeed.feedparser.exceptions import DuplicateError
from radiofeed.feedparser.jobs import parse_feed, parse_feeds
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import PodcastFactory


class TestParseFeed:
    @pytest.fixture
    def mock_parse_ok(self, mocker):
        return mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
        )

    @pytest.fixture
    def mock_parse_fail(self, mocker):
        return mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
            side_effect=DuplicateError(),
        )

    @pytest.mark.django_db()(transaction=True)
    def test_ok(self, mock_parse_ok, podcast):
        assert parse_feed(podcast.pk) == "success"
        mock_parse_ok.assert_called()

    @pytest.mark.django_db()(transaction=True)
    def test_inactive(self, mock_parse_ok):
        podcast = PodcastFactory(active=False)
        with pytest.raises(Podcast.DoesNotExist):
            parse_feed(podcast.pk)
        mock_parse_ok.assert_not_called()

    @pytest.mark.django_db()(transaction=True)
    def test_feed_parser_error(self, mock_parse_fail, podcast):
        assert parse_feed(podcast.pk) == "duplicate"
        mock_parse_fail.assert_called()


class TestParseFeeds:
    @pytest.fixture
    def mock_parse_feed(self, mocker):
        return mocker.patch(
            "radiofeed.feedparser.jobs.parse_feed.delay",
        )

    @pytest.mark.django_db
    def test_ok(self, mock_parse_feed):
        podcast = PodcastFactory(pub_date=None)
        parse_feeds()
        mock_parse_feed.assert_called()
        podcast.refresh_from_db()
        assert podcast.queued is not None

    @pytest.mark.django_db
    def test_queued(self, mock_parse_feed):
        PodcastFactory(pub_date=None, queued=timezone.now())
        parse_feeds()
        mock_parse_feed.assert_not_called()

    @pytest.mark.django_db
    def test_inactive(self, mock_parse_feed):
        PodcastFactory(pub_date=None, active=False)
        parse_feeds()
        mock_parse_feed.assert_not_called()
