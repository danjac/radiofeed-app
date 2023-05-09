import pytest
from django.core.management import call_command

from radiofeed.feedparser.exceptions import Duplicate
from radiofeed.podcasts.factories import create_podcast


class TestParseFeeds:
    @pytest.mark.django_db
    def test_ok(self, mocker):
        create_podcast(pub_date=None)
        patched = mocker.patch(
            "radiofeed.feedparser.feed_parser.FeedParser.parse",
        )
        call_command("parse_feeds", limit=200)
        patched.assert_called()

    @pytest.mark.django_db
    def test_feed_parser_error(self, mocker):
        create_podcast(pub_date=None)
        patched = mocker.patch(
            "radiofeed.feedparser.feed_parser.FeedParser.parse",
            side_effect=Duplicate(),
        )
        call_command("parse_feeds", limit=200)
        patched.assert_called()
