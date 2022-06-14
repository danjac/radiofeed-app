from datetime import timedelta

from radiofeed.episodes.tasks import send_new_episodes_email


class TestTasks:
    def test_send_recommendations_email(self, mocker):
        patched = mocker.patch("radiofeed.episodes.emails.send_new_episodes_email")
        since = timedelta(days=7)
        send_new_episodes_email(1234, since)
        patched.assert_called_with(1234, since)
