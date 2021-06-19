import datetime

from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone

from audiotrails.podcasts import tasks
from audiotrails.podcasts.factories import PodcastFactory
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


class CreatePodcastRecommendationsTests(TestCase):
    @patch("audiotrails.podcasts.tasks.recommend", autospec=True)
    def test_create_podcast_recommendations(self, mock_recommend) -> None:
        tasks.create_podcast_recommendations()
        mock_recommend.assert_called()


class CrawlItunesTests(TestCase):
    @patch("audiotrails.podcasts.tasks.itunes.crawl_itunes", autospec=True)
    def test_crawl_itunes(self, mock_crawl_itunes) -> None:
        tasks.crawl_itunes()
        mock_crawl_itunes.assert_called()


class SyncPodcastFeedsTests(TestCase):
    @patch(
        "audiotrails.podcasts.tasks.sync_podcast_feed.delay",
        autospec=True,
    )
    def test_podcast_just_updated(self, mock_sync_podcast_feed: Mock) -> None:
        PodcastFactory(pub_date=timezone.now())
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_not_called()

    @patch(
        "audiotrails.podcasts.tasks.sync_podcast_feed.delay",
        autospec=True,
    )
    def test_podcast_updated_more_than_12_hours_ago(
        self, mock_sync_podcast_feed: Mock
    ) -> None:
        PodcastFactory(pub_date=timezone.now() - datetime.timedelta(hours=24))
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_called()


class TestSyncPodcastFeed(TestCase):
    @patch(
        "audiotrails.podcasts.tasks.parse_feed",
        autospec=True,
    )
    def test_no_podcast_found(self, mock_parse_feed: Mock) -> None:
        tasks.sync_podcast_feed(12345)
        mock_parse_feed.assert_not_called()

    @patch(
        "audiotrails.podcasts.tasks.parse_feed",
        autospec=True,
    )
    def test_ok(self, mock_parse_feed: Mock) -> None:
        podcast = PodcastFactory()
        tasks.sync_podcast_feed(podcast.rss)
        mock_parse_feed.assert_called()
