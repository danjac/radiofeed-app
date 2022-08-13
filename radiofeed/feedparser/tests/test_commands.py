from __future__ import annotations

from django.core.management import call_command


class TestFeedUpdates:
    def test_command(self, mocker, podcast):
        patched = mocker.patch("radiofeed.feedparser.feed_parser.FeedParser.parse")
        call_command("feed_updater", limit=200)
        patched.assert_called()

    def test_parse_exception(self, mocker, podcast):
        patched = mocker.patch(
            "radiofeed.feedparser.feed_parser.FeedParser.parse",
            side_effect=ValueError("oops"),
        )
        call_command("feed_updater", limit=200)
        patched.assert_called()
