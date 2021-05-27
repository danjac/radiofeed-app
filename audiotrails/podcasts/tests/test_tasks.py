import datetime

from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone

from audiotrails.podcasts import tasks
from audiotrails.podcasts.factories import PodcastFactory
from audiotrails.shared.feed_parser import RssParserError
from audiotrails.users.factories import UserFactory


class SendRecommendationEmailsTests(TestCase):
    @patch(
        "audiotrails.podcasts.tasks.send_recommendations_email",
        autospec=True,
    )
    def test_send_if_user_inactive(self, mock_send_email: Mock) -> None:
        UserFactory(is_active=False, send_recommendations_email=True)
        tasks.send_recommendation_emails()
        mock_send_email.assert_not_called()

    @patch(
        "audiotrails.podcasts.tasks.send_recommendations_email",
        autospec=True,
    )
    def test_send_if_user_emails_off(self, mock_send_email: Mock) -> None:
        UserFactory(is_active=True, send_recommendations_email=False)
        tasks.send_recommendation_emails()
        mock_send_email.assert_not_called()

    @patch(
        "audiotrails.podcasts.tasks.send_recommendations_email",
        autospec=True,
    )
    def test_send_if_user_emails_on(self, mock_send_email: Mock) -> None:
        UserFactory(is_active=True, send_recommendations_email=True)
        tasks.send_recommendation_emails()
        mock_send_email.assert_called()


class SyncPodcastFeedsTests(TestCase):
    @patch(
        "audiotrails.podcasts.tasks.sync_podcast_feed.delay",
        autospec=True,
    )
    def test_podcast_has_too_many_retries(self, mock_sync_podcast_feed: Mock) -> None:
        PodcastFactory(num_retries=3)
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_not_called()

    @patch(
        "audiotrails.podcasts.tasks.sync_podcast_feed.delay",
        autospec=True,
    )
    def test_podcast_just_updated(self, mock_sync_podcast_feed: Mock) -> None:
        PodcastFactory(last_updated=timezone.now())
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_not_called()

    @patch(
        "audiotrails.podcasts.tasks.sync_podcast_feed.delay",
        autospec=True,
    )
    def test_podcast_never_updated(self, mock_sync_podcast_feed: Mock) -> None:
        PodcastFactory(last_updated=None)
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_called()

    @patch(
        "audiotrails.podcasts.tasks.sync_podcast_feed.delay",
        autospec=True,
    )
    def test_podcast_updated_more_than_12_hours_ago(
        self, mock_sync_podcast_feed: Mock
    ) -> None:
        PodcastFactory(last_updated=timezone.now() - datetime.timedelta(hours=24))
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_called()


class TestSyncPodcastFeed(TestCase):
    @patch(
        "audiotrails.podcasts.models.Podcast.sync_rss_feed",
        autospec=True,
    )
    def test_no_podcast_found(self, mock_parse_rss: Mock) -> None:
        tasks.sync_podcast_feed(12345)
        mock_parse_rss.assert_not_called()

    @patch(
        "audiotrails.podcasts.models.Podcast.sync_rss_feed",
        autospec=True,
    )
    def test_parser_exception(self, mock_parse_rss: Mock) -> None:
        podcast = PodcastFactory()
        mock_parse_rss.side_effect = RssParserError("Boom")
        tasks.sync_podcast_feed(podcast.rss)

    @patch(
        "audiotrails.podcasts.models.Podcast.sync_rss_feed",
        autospec=True,
    )
    def test_ok(self, mock_parse_rss: Mock) -> None:
        podcast = PodcastFactory()
        tasks.sync_podcast_feed(podcast.rss)
        mock_parse_rss.assert_called()
