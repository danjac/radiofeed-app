import pytest
from django.core.management import call_command


class TestSendNewEpisodesEmails:
    @pytest.mark.django_db()(transaction=True)
    def test_send_emails(self, mocker, user):
        patched = mocker.patch("radiofeed.episodes.emails.send_new_episodes_email")
        call_command("send_new_episodes_emails")
        patched.assert_called()
