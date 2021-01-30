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
def mock_rss_parser(mocker):
    return mocker.patch("radiofeed.podcasts.tasks.RssParser")


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
    def test_sync_podcast_feed_if_no_podcast_found(self, mock_rss_parser):
        tasks.sync_podcast_feed(12345)
        mock_rss_parser.parse_from_podcast.assert_not_called()

    def test_sync_podcast_feed_if_http_error(self, mock_rss_parser, podcast):
        mock_rss_parser.parse_from_podcast.side_effect = requests.HTTPError("Boom")
        tasks.sync_podcast_feed(podcast.rss)

    def test_sync_podcast_feed_no_errors(self, mock_rss_parser, podcast):
        tasks.sync_podcast_feed(podcast.rss)
        mock_rss_parser.parse_from_podcast.assert_called()
