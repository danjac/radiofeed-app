import pytest
from django.core.management import call_command

from radiofeed.feedparser.exceptions import Duplicate
from radiofeed.podcasts.factories import create_podcast


class TestParseFeeds:
    @pytest.fixture
    def mock_parse_ok(self, mocker):
        yield mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
        )

    @pytest.fixture
    def mock_parse_fail(self, mocker):
        yield mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed", side_effect=Duplicate()
        )

    @pytest.mark.django_db
    def test_ok(self, mock_parse_ok):
        create_podcast(pub_date=None)
        call_command("parse_feeds", limit=200)
        mock_parse_ok.assert_called()

    @pytest.mark.django_db
    def test_feed_parser_error(self, mock_parse_fail):
        create_podcast(pub_date=None)
        call_command("parse_feeds", limit=200)
        mock_parse_fail.assert_called()
