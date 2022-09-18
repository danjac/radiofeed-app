from __future__ import annotations

from django.core.management import call_command

from radiofeed.feedparser.feed_parser import Result
from radiofeed.podcasts.factories import PodcastFactory
from radiofeed.podcasts.models import Podcast


class TestParseFeeds:
    def test_command(self, db, mocker):
        podcast = PodcastFactory(pub_date=None)
        patched = mocker.patch(
            "radiofeed.feedparser.feed_parser.parse_feed",
            return_value=Result(podcast, Podcast.ParseResult.SUCCESS),
        )
        call_command("parse_feeds", limit=200)
        patched.assert_called_with(podcast)
