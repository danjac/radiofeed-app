import pytest
from django.core.management import call_command

from radiofeed.users.tests.factories import EmailAddressFactory


class TestSendEpisodeNotifications:
    @pytest.fixture
    def recipient(self):
        return EmailAddressFactory(verified=True, primary=True)

    @pytest.fixture
    def mock_task(self, mocker):
        return mocker.patch(
            "radiofeed.episodes.management.commands.send_episode_updates.send_episode_updates"
        )

    @pytest.mark.django_db
    def test_has_episodes(self, recipient, mock_task):
        call_command("send_episode_updates")
        mock_task.enqueue.assert_called()
