from radiofeed.podcasts.tasks import parse_feed, send_recommendations_email


class TestTasks:
    def test_parse_feed(self, mocker, podcast):
        patched = mocker.patch("radiofeed.podcasts.feed_parser.FeedParser")
        parse_feed(podcast.id)
        patched.assert_called_with(podcast)

    def test_recommendations_email(self, mocker, user):
        patched = mocker.patch("radiofeed.podcasts.emails.send_recommendations_email")
        send_recommendations_email(user.id)
        patched.assert_called_with(user)
