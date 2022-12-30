from __future__ import annotations

from django.core.management import call_command

from radiofeed.feedparser import feed_parser
from radiofeed.podcasts.factories import create_podcast


class TestParseFeeds:
    def test_ok(self, db, mocker):
        create_podcast(pub_date=None)
        patched = mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
        )
        call_command("parse_feeds", limit=200)
        patched.assert_called()

    def test_feed_parser_error(self, db, mocker):
        create_podcast(pub_date=None)
        patched = mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
            side_effect=feed_parser.Duplicate(),
        )
        call_command("parse_feeds", limit=200)
        patched.assert_called()
