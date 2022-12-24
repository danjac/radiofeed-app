from __future__ import annotations

import httpx

from django.core.management import call_command

from radiofeed.feedparser import feed_parser, rss_parser
from radiofeed.podcasts.factories import create_podcast


class TestParseFeeds:
    def test_ok(self, db, mocker):
        create_podcast(pub_date=None)
        patched = mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
        )
        call_command("parse_feeds", limit=200)
        patched.assert_called()

    def test_duplicate(self, db, mocker):
        create_podcast(pub_date=None)
        patched = mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
            side_effect=feed_parser.Duplicate(),
        )
        call_command("parse_feeds", limit=200)
        patched.assert_called()

    def test_inaccessible(self, db, mocker):
        create_podcast(pub_date=None)
        patched = mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
            side_effect=feed_parser.Inaccessible(),
        )
        call_command("parse_feeds", limit=200)
        patched.assert_called()

    def test_not_modified(self, db, mocker):
        create_podcast(pub_date=None)
        patched = mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
            side_effect=feed_parser.NotModified(),
        )
        call_command("parse_feeds", limit=200)
        patched.assert_called()

    def test_rss_error(self, db, mocker):
        create_podcast(pub_date=None)
        patched = mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
            side_effect=rss_parser.RssParserError("unknown error"),
        )
        call_command("parse_feeds", limit=200)
        patched.assert_called()

    def test_http_error(self, db, mocker):
        create_podcast(pub_date=None)
        patched = mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
            side_effect=httpx.HTTPError("error"),
        )
        call_command("parse_feeds", limit=200)
        patched.assert_called()
