from __future__ import annotations

from django.core.management import call_command

from radiofeed.podcasts.factories import PodcastFactory


class TestParseFeeds:
    def test_command(self, db, mocker):
        podcast = PodcastFactory(pub_date=None)
        patched = mocker.patch("radiofeed.feedparser.feed_parser.parse_feed")
        call_command("parse_feeds", limit=200)
        patched.assert_called_with(podcast)
