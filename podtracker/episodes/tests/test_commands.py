from datetime import timedelta

from django.core.management import call_command

from podtracker.users.factories import UserFactory


class TestSendNewEpisodesEmails:
    def test_command(self, db, mocker):

        yes = UserFactory(send_email_notifications=True)
        UserFactory(send_email_notifications=False)
        UserFactory(send_email_notifications=True, is_active=False)

        mock_send = mocker.patch(
            "podtracker.episodes.emails.send_new_episodes_email.delay"
        )

        call_command("send_new_episodes_emails")

        assert len(mock_send.mock_calls) == 1
        assert mock_send.call_args == (
            (
                yes,
                timedelta(days=7),
            ),
        )
