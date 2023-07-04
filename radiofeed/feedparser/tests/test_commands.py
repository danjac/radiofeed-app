import pytest
from django.core.management import call_command

from radiofeed.feedparser.exceptions import DuplicateError
from radiofeed.podcasts.tests.factories import create_podcast


class TestParseFeeds:
    @pytest.fixture()
    def mock_parse_ok(self, mocker):
        return mocker.patch(
            "radiofeed.feedparser.feed_parser.FeedParser.parse",
        )

    @pytest.fixture()
    def mock_parse_fail(self, mocker):
        return mocker.patch(
            "radiofeed.feedparser.feed_parser.FeedParser.parse",
            side_effect=DuplicateError(),
        )

    @pytest.mark.django_db()(transaction=True)
    def test_ok(self, mock_parse_ok):
        create_podcast(pub_date=None)
        call_command("parse_feeds")
        mock_parse_ok.assert_called()

    @pytest.mark.django_db()(transaction=True)
    def test_not_scheduled(self, mock_parse_ok):
        create_podcast(active=False)
        call_command("parse_feeds")
        mock_parse_ok.assert_not_called()

    @pytest.mark.django_db()(transaction=True)
    def test_feed_parser_error(self, mock_parse_fail):
        create_podcast(pub_date=None)
        call_command("parse_feeds")
        mock_parse_fail.assert_called()
