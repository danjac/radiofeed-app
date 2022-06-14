from radiofeed.podcasts.tasks import feed_update, send_recommendations_email


class TestTasks:
    def test_feed_update(self, mocker):
        patched = mocker.patch("radiofeed.podcasts.feed_updater.update")
        feed_update(1234)
        patched.assert_called_with(1234)

    def test_send_recommendations_email(self, mocker):
        patched = mocker.patch("radiofeed.podcasts.emails.send_recommendations_email")
        send_recommendations_email(1234)
        patched.assert_called_with(1234)
