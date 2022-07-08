from __future__ import annotations

from radiofeed.feedparser.tasks import parse_feed


class TestTasks:
    def test_parse_feed(self, mocker, podcast):
        patched = mocker.patch("radiofeed.feedparser.tasks.FeedParser")
        parse_feed(podcast.id)
        patched.assert_called_with(podcast)
