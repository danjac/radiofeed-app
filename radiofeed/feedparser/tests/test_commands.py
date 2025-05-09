import pytest
from django.core.management import call_command

from radiofeed.feedparser.exceptions import DuplicateError
from radiofeed.podcasts.tests.factories import PodcastFactory


class TestParseFeeds:
    _PARSE_FEED = "radiofeed.feedparser.management.commands.parse_feeds.parse_feed"

    @pytest.fixture
    def mock_parse_ok(self, mocker):
        return mocker.patch(self._PARSE_FEED)

    @pytest.fixture
    def mock_parser_error(self, mocker):
        return mocker.patch(self._PARSE_FEED, side_effect=DuplicateError())

    @pytest.fixture
    def mock_parse_exception(self, mocker):
        return mocker.patch(self._PARSE_FEED, side_effect=RuntimeError())

    @pytest.mark.django_db()(transaction=True)
    def test_ok(self, mock_parse_ok):
        PodcastFactory(pub_date=None)
        call_command("parse_feeds")
        mock_parse_ok.assert_called()

    @pytest.mark.django_db()(transaction=True)
    def test_not_scheduled(self, mock_parse_ok):
        PodcastFactory(active=False)
        call_command("parse_feeds")
        mock_parse_ok.assert_not_called()

    @pytest.mark.django_db()(transaction=True)
    def test_feed_parser_error(self, mock_parser_error):
        PodcastFactory(pub_date=None)
        call_command("parse_feeds")
        mock_parser_error.assert_called()

    @pytest.mark.django_db()(transaction=True)
    def test_feed_other_exception(self, mock_parse_exception):
        PodcastFactory(pub_date=None)
        call_command("parse_feeds")
        mock_parse_exception.assert_called()
