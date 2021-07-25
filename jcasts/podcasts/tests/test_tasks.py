import datetime

import pytest

from django.utils import timezone

from jcasts.podcasts import tasks
from jcasts.podcasts.factories import PodcastFactory
from jcasts.users.factories import UserFactory


class TestSendRecommendationEmails:
    @pytest.fixture
    def mock_send_email(self, mocker):
        return mocker.patch(
            "jcasts.podcasts.tasks.send_recommendations_email",
            autospec=True,
        )

    def test_send_if_user_inactive(self, db, mock_send_email):
        UserFactory(is_active=False, send_recommendations_email=True)
        tasks.send_recommendation_emails()
        mock_send_email.assert_not_called()

    def test_send_if_user_emails_off(self, db, mock_send_email):
        UserFactory(is_active=True, send_recommendations_email=False)
        tasks.send_recommendation_emails()
        mock_send_email.assert_not_called()

    def test_send_if_user_emails_on(self, db, mock_send_email):
        UserFactory(is_active=True, send_recommendations_email=True)
        tasks.send_recommendation_emails()
        mock_send_email.assert_called()


class TestCreatePodcastRecommendationsTests:
    def test_create_podcast_recommendations(self, db, mocker):
        mock_recommend = mocker.patch("jcasts.podcasts.tasks.recommend", autospec=True)
        tasks.create_podcast_recommendations()
        mock_recommend.assert_called()


class TestCrawlItunes:
    def test_crawl_itunes(self, db, mocker):
        mock_crawl_itunes = mocker.patch(
            "jcasts.podcasts.tasks.itunes.crawl_itunes", autospec=True
        )

        tasks.crawl_itunes()
        mock_crawl_itunes.assert_called()


class TestSyncPodcastFeedsTests:
    @pytest.fixture
    def mock_sync_podcast_feed(self, mocker):
        return mocker.patch(
            "jcasts.podcasts.tasks.sync_podcast_feed.delay",
            autospec=True,
        )

    def test_podcast_just_updated(self, db, mock_sync_podcast_feed):
        podcast = PodcastFactory(pub_date=timezone.now())
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_not_called()
        podcast.refresh_from_db()
        assert not podcast.last_checked

    def test_podcast_updated_more_than_12_hours_ago(self, db, mock_sync_podcast_feed):
        podcast = PodcastFactory(pub_date=timezone.now() - datetime.timedelta(hours=24))
        tasks.sync_podcast_feeds()
        mock_sync_podcast_feed.assert_called()
        podcast.refresh_from_db()
        assert podcast.last_checked


class TestSyncPodcastFeed:
    @pytest.fixture
    def mock_parse_feed(self, mocker):
        return mocker.patch(
            "jcasts.podcasts.tasks.parse_feed",
            autospec=True,
        )

    def test_no_podcast_found(self, db, mock_parse_feed):
        tasks.sync_podcast_feed(12345)
        mock_parse_feed.assert_not_called()

    def test_ok(self, db, podcast, mock_parse_feed):
        tasks.sync_podcast_feed(podcast.rss)
        mock_parse_feed.assert_called()

    def test_pc_complete(self, db, podcast, mock_parse_feed):
        tasks.sync_podcast_feed(podcast.rss, pc_complete=35)
        mock_parse_feed.assert_called()
