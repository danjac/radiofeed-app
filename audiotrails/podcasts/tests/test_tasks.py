import datetime

from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from audiotrails.users.factories import UserFactory

from .. import tasks
from ..factories import PodcastFactory
from ..rss_parser import RssParserError


class SendRecommendationEmailsTests(TestCase):
    @patch(
        "audiotrails.podcasts.tasks.send_recommendations_email",
        autospec=True,
    )
    def test_send_if_user_inactive(self, mock_send_email):
        UserFactory(is_active=False, send_recommendations_email=True)
        tasks.send_recommendation_emails()
        mock_send_email.assert_not_called()

    @patch(
        "audiotrails.podcasts.tasks.send_recommendations_email",
        autospec=True,
    )
    def test_send_if_user_emails_off(self, mock_send_email):
        UserFactory(is_active=True, send_recommendations_email=False)
        tasks.send_recommendation_emails()
        mock_send_email.assert_not_called()

    @patch(
        "audiotrails.podcasts.tasks.send_recommendations_email",
        autospec=True,
    )
    def test_send_if_user_emails_on(self, mock_send_email):
        UserFactory(is_active=True, send_recommendations_email=True)
        tasks.send_recommendation_emails()
        mock_send_email.assert_called()


class SyncPodcastFeedsTests(TestCase):
    @patch(
        "audiotrails.podcasts.tasks.sync_podcast_feed.delay",
        autospec=True,
    )
    def test_podcast_has_too_many_retries(self, mock_sync_podcast_feed):
        PodcastFactory(num_retries=3)
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_not_called()

    @patch(
        "audiotrails.podcasts.tasks.sync_podcast_feed.delay",
        autospec=True,
    )
    def test_podcast_just_updated(self, mock_sync_podcast_feed):
        PodcastFactory(last_updated=timezone.now())
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_not_called()

    @patch(
        "audiotrails.podcasts.tasks.sync_podcast_feed.delay",
        autospec=True,
    )
    def test_podcast_never_updated(self, mock_sync_podcast_feed):
        PodcastFactory(last_updated=None)
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_called()

    @patch(
        "audiotrails.podcasts.tasks.sync_podcast_feed.delay",
        autospec=True,
    )
    def test_podcast_updated_more_than_12_hours_ago(self, mock_sync_podcast_feed):
        PodcastFactory(last_updated=timezone.now() - datetime.timedelta(hours=24))
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_called()


class TestSyncPodcastFeed:
    @patch(
        "audiotrails.podcasts.tasks.parse_rss",
        autospec=True,
    )
    def test_no_podcast_found(self, mock_parse_rss):
        tasks.sync_podcast_feed(12345)
        mock_parse_rss.assert_not_called()

    @patch(
        "audiotrails.podcasts.tasks.parse_rss",
        autospec=True,
    )
    def test_parser_exception(self, mock_parse_rss, podcast):
        mock_parse_rss.side_effect = RssParserError("Boom")
        tasks.sync_podcast_feed(podcast.rss)

    @patch(
        "audiotrails.podcasts.tasks.parse_rss",
        autospec=True,
    )
    def test_ok(self, mock_parse_rss, podcast):
        tasks.sync_podcast_feed(podcast.rss)
        mock_parse_rss.assert_called()
