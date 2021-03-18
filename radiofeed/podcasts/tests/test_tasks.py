import datetime

import pytest

from django.utils import timezone

from radiofeed.users.factories import UserFactory

from .. import tasks
from ..factories import PodcastFactory
from ..rss_parser import RssParserException

pytestmark = pytest.mark.django_db


@pytest.fixture
def mock_send_email(mocker):
    return mocker.patch(
        "radiofeed.podcasts.tasks.send_recommendations_email",
        autospec=True,
    )


@pytest.fixture
def mock_sync_podcast_feed(mocker):
    return mocker.patch(
        "radiofeed.podcasts.tasks.sync_podcast_feed.delay",
        autospec=True,
    )


@pytest.fixture
def mock_parse_rss(mocker):
    return mocker.patch(
        "radiofeed.podcasts.tasks.parse_rss",
        autospec=True,
    )


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


class TestSyncPodcastFeeds:
    def test_podcast_has_too_many_retries(self, mock_sync_podcast_feed):
        PodcastFactory(num_retries=3)
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_not_called()

    def test_podcast_just_updated(self, mock_sync_podcast_feed):
        PodcastFactory(last_updated=timezone.now())
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_not_called()

    def test_podcast_never_updated(self, mock_sync_podcast_feed):
        PodcastFactory(last_updated=None)
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_called()

    def test_podcast_updated_more_than_12_hours_ago(self, mock_sync_podcast_feed):
        PodcastFactory(last_updated=timezone.now() - datetime.timedelta(hours=24))
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_called()


class TestSyncPodcastFeed:
    def test_no_podcast_found(self, mock_parse_rss):
        tasks.sync_podcast_feed(12345)
        mock_parse_rss.assert_not_called()

    def test_parser_exception(self, mock_parse_rss, podcast):
        mock_parse_rss.side_effect = RssParserException("Boom")
        tasks.sync_podcast_feed(podcast.rss)

    def test_ok(self, mock_parse_rss, podcast):
        tasks.sync_podcast_feed(podcast.rss)
        mock_parse_rss.assert_called()
