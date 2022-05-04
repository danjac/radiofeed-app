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
        sent = []

        class MockSend:
            def __init__(self, user_id, *args, **kwargs):
                self.user_id = user_id

            def __call__(self):
                sent.append(self.user_id)

        send = UserFactory(send_email_notifications=True)
        not_send = UserFactory(send_email_notifications=False)

        mocker.patch("radiofeed.episodes.tasks.send_new_episodes_email", MockSend)

        send_new_episodes_emails()

        assert send.id in sent
        assert not_send.id not in sent
