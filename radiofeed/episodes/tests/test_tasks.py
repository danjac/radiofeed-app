from datetime import timedelta

from radiofeed.episodes.tasks import send_new_episodes_email


class TestTasks:
    def test_send_recommendations_email(self, mocker, user):
        patched = mocker.patch("radiofeed.episodes.emails.send_new_episodes_email")
        since = timedelta(days=7)
        send_new_episodes_email(user.id, since)
        patched.assert_called_with(user, since)
