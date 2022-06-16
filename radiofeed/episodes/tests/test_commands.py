from datetime import timedelta

from django.core.management import call_command

from radiofeed.users.factories import UserFactory


class TestCommands:
    def test_send_new_episodes_emails(self, db, mocker):
        user = UserFactory(send_email_notifications=True)

        patched = mocker.patch("radiofeed.episodes.tasks.send_new_episodes_email")

        call_command("send_new_episodes_emails")

        patched.assert_called_with(user.id, interval=timedelta(days=7))
