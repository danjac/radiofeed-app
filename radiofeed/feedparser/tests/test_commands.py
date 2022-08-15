from __future__ import annotations

from django.core.management import call_command


class TestFeedUpdates:
    def test_command(self, mocker, podcast):
        patched = mocker.patch("radiofeed.feedparser.scheduler.schedule_for_update")
        call_command("feed_updater", limit=200)
        patched.assert_called_with(200)
