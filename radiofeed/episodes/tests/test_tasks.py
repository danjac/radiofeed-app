from datetime import timedelta

from radiofeed.episodes.tasks import send_new_episodes_email, send_new_episodes_emails
from radiofeed.users.factories import UserFactory


class TestTasks:
    def test_send_new_episodes_email(self, user, mocker):
        patched = mocker.patch("radiofeed.episodes.emails.send_new_episodes_email")
        since = timedelta(days=7)
        send_new_episodes_email(user.id, since)
        patched.assert_called_with(user, since)

    def test_send_new_episodes_email_no_user(self, db, mocker):
        patched = mocker.patch("radiofeed.episodes.emails.send_new_episodes_email")
        send_new_episodes_email(1234, timedelta(days=7))
        patched.assert_not_called()

    def test_send_new_episodes_emails(self, db, mocker):
        user = UserFactory(send_email_notifications=True)
        UserFactory(send_email_notifications=False)

        patched = mocker.patch("radiofeed.episodes.tasks.send_new_episodes_email.map")

        send_new_episodes_emails()

        patched.assert_called_with([(user.id, timedelta(days=7))])
