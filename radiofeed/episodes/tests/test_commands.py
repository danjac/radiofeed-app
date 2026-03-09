import pytest
from django.core.management import call_command


@pytest.mark.django_db
class TestSendEpisodeNotifications:
    @pytest.fixture
    def mock_task(self, mocker):
        return mocker.patch("radiofeed.episodes.tasks.send_episode_updates")

    def test_has_episodes(self, recipient, mock_task):
        call_command("send_episode_updates")
        mock_task.enqueue.assert_called()
