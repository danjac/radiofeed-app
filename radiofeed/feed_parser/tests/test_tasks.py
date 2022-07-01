from radiofeed.feed_parser.tasks import parse_feed


class TestTasks:
    def test_parse_feed(self, mocker, podcast):
        patched = mocker.patch("radiofeed.feed_parser.tasks.FeedParser")
        parse_feed(podcast.id)
        patched.assert_called_with(podcast)
