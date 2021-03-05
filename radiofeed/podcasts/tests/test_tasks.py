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
def mock_parse_rss(mocker):
    return mocker.patch("radiofeed.podcasts.tasks.parse_rss")


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
    def test_sync_podcast_feed_if_no_podcast_found(self, mock_parse_rss):
        tasks.sync_podcast_feed(12345)
        mock_parse_rss.assert_not_called()

    def test_sync_podcast_feed_if_http_error(self, mock_parse_rss, podcast):
        mock_parse_rss.side_effect = requests.HTTPError("Boom")
        tasks.sync_podcast_feed(podcast.rss)

    def test_sync_podcast_feed_no_errors(self, mock_parse_rss, podcast):
        tasks.sync_podcast_feed(podcast.rss)
        mock_parse_rss.assert_called()
