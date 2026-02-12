import pytest
from django.core.management import call_command

from radiofeed.podcasts.tests.factories import (
    RecommendationFactory,
    SubscriptionFactory,
)
from radiofeed.users.tests.factories import EmailAddressFactory


@pytest.fixture
def recipient():
    return EmailAddressFactory(verified=True, primary=True)


class TestSendEpisodeNotifications:
    @pytest.fixture
    def mock_task(self, mocker):
        return mocker.patch(
            "radiofeed.users.management.commands.notifications.tasks.send_episode_updates"
        )

    @pytest.mark.django_db
    def test_has_episodes(self, recipient, mock_task):
        call_command("notifications", "episode-updates")
        mock_task.enqueue.assert_called()


class TestSendPodcastRecommendations:
    @pytest.fixture
    def mock_task(self, mocker):
        return mocker.patch(
            "radiofeed.users.management.commands.notifications.tasks.send_podcast_recommendations"
        )

    @pytest.fixture
    def recipient(self):
        return EmailAddressFactory(verified=True, primary=True)

    @pytest.mark.django_db
    def test_ok(self, recipient, mock_task):
        podcast = SubscriptionFactory(subscriber=recipient.user).podcast
        RecommendationFactory(podcast=podcast)
        call_command("notifications", "podcast-recommendations")
        mock_task.enqueue.assert_called()
