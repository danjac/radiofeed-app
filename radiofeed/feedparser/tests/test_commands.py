from __future__ import annotations

from django.core.management import call_command


class TestFeedUpdates:
    def test_command(self, mocker, podcast):

        patched = mocker.patch("radiofeed.feedparser.tasks.parse_feed.delay")

        call_command("feed_updater", limit=200)

        patched.assert_called_with(podcast.id)
