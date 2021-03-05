# Third Party Libraries
import pytest
import requests

# RadioFeed
from radiofeed.users.factories import UserFactory

# Local
from .. import tasks

pytestmark = pytest.mark.django_db


@pytest.fixture
def mock_send_email(mocker):
    return mocker.patch("radiofeed.podcasts.tasks.send_recommendations_email")


@pytest.fixture
def mock_sync_rss_feed(mocker):
    return mocker.patch("radiofeed.podcasts.tasks.sync_rss_feed")


class TestSendRecommendationEmails:
    def test_send_if_user_inactive(self, mock_send_email):
        UserFactory(is_active=False, send_recommendations_email=True)
        tasks.send_recommendation_emails()
        mock_send_email.assert_not_called()

    def test_send_if_user_emails_off(self, mock_send_email):
        UserFactory(is_active=True, send_recommendations_email=False)
        tasks.send_recommendation_emails()
        mock_send_email.assert_not_called()

    def test_send_if_user_emails_on(self, mock_send_email):
        UserFactory(is_active=True, send_recommendations_email=True)
        tasks.send_recommendation_emails()
        mock_send_email.assert_called()


class TestSyncPodcastFeed:
    def test_sync_podcast_feed_if_no_podcast_found(self, mock_sync_rss_feed):
        tasks.sync_podcast_feed(12345)
        mock_sync_rss_feed.assert_not_called()

    def test_sync_podcast_feed_if_http_error(self, mock_sync_rss_feed, podcast):
        mock_sync_rss_feed.side_effect = requests.HTTPError("Boom")
        tasks.sync_podcast_feed(podcast.rss)

    def test_sync_podcast_feed_no_errors(self, mock_sync_rss_feed, podcast):
        tasks.sync_podcast_feed(podcast.rss)
        mock_sync_rss_feed.assert_called()
