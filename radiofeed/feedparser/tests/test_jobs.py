import pytest

from radiofeed.feedparser.exceptions import DuplicateError
from radiofeed.feedparser.jobs import parse_feeds
from radiofeed.podcasts.tests.factories import PodcastFactory


class TestParseFeeds:
    @pytest.fixture
    def mock_parse_ok(self, mocker):
        return mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
        )

    @pytest.fixture
    def mock_parser_error(self, mocker):
        return mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
            side_effect=DuplicateError(),
        )

    @pytest.fixture
    def mock_parse_exception(self, mocker):
        return mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
            side_effect=RuntimeError(),
        )

    @pytest.mark.django_db()(transaction=True)
    def test_ok(self, mock_parse_ok):
        PodcastFactory(pub_date=None)
        parse_feeds()
        mock_parse_ok.assert_called()

    @pytest.mark.django_db()(transaction=True)
    def test_not_scheduled(self, mock_parse_ok):
        PodcastFactory(active=False)
        parse_feeds()
        mock_parse_ok.assert_not_called()

    @pytest.mark.django_db()(transaction=True)
    def test_feed_parser_error(self, mock_parser_error):
        PodcastFactory(pub_date=None)
        parse_feeds()
        mock_parser_error.assert_called()

    @pytest.mark.django_db()(transaction=True)
    def test_feed_other_exception(self, mock_parse_exception):
        PodcastFactory(pub_date=None)
        parse_feeds()
        mock_parse_exception.assert_called()
