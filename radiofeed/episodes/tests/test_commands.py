from datetime import timedelta

from django.core.management import call_command

from radiofeed.users.factories import UserFactory


class TestCommands:
    def test_send_new_episodes_emails(self, db, mocker):
        user = UserFactory(send_email_notifications=True)
        UserFactory(send_email_notifications=False)

        patched = mocker.patch("radiofeed.episodes.tasks.send_new_episodes_email.map")

        call_command("send_new_episodes_emails")

        patched.assert_called_with([(user.id, timedelta(days=7))])
