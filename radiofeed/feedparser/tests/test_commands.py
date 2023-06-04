import pytest
from django.core.management import call_command
from django.utils import timezone

from radiofeed.feedparser.exceptions import Duplicate
from radiofeed.podcasts.factories import create_podcast


class TestParseFeeds:
    @pytest.fixture
    def mock_parse_ok(self, mocker):
        yield mocker.patch(
            "radiofeed.feedparser.feed_parser.FeedParser.parse",
        )

    @pytest.fixture
    def mock_parse_fail(self, mocker):
        yield mocker.patch(
            "radiofeed.feedparser.feed_parser.FeedParser.parse", side_effect=Duplicate()
        )

    @pytest.mark.django_db(transaction=True)
    def test_ok(self, mock_parse_ok):
        create_podcast(queued=timezone.now())
        call_command("parse_feeds")
        mock_parse_ok.assert_called()

    @pytest.mark.django_db(transaction=True)
    def test_scheduled(self, mock_parse_ok):
        create_podcast(queued=None)
        call_command("parse_feeds")
        mock_parse_ok.assert_called()

    @pytest.mark.django_db(transaction=True)
    def test_feed_parser_error(self, mock_parse_fail):
        create_podcast(queued=timezone.now())
        call_command("parse_feeds")
        mock_parse_fail.assert_called()
