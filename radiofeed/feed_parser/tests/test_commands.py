from django.core.management import call_command


class TestFeedUpdates:
    def test_command(self, mocker, podcast):

        patched = mocker.patch("radiofeed.feed_parser.tasks.parse_feed.map")

        call_command("feed_updates", limit=200)

        patched.assert_called()
