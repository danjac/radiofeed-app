from datetime import timedelta

from podtracker.episodes.tasks import send_new_episodes_email


class TestTasks:
    def test_send_new_episodes_email(self, user, mocker):
        patched = mocker.patch("podtracker.episodes.emails.send_new_episodes_email")
        since = timedelta(days=7)
        send_new_episodes_email(user.id, since)
        patched.assert_called_with(user, since)
