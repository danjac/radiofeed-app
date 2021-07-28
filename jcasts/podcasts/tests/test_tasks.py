from datetime import timedelta

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


class TestSchedulePodcastFeedsTests:
    @pytest.fixture
    def mock_sync_podcast_feed(self, mocker):
        return mocker.patch(
            "jcasts.podcasts.tasks.sync_podcast_feed.apply_async",
            autospec=True,
        )

    def test_schedule_podcast_feeds(self, db, mock_sync_podcast_feed):
        now = timezone.now()

        PodcastFactory(
            frequency=timedelta(days=1),
            pub_date=(now - timedelta(days=7)).replace(hour=now.hour),
            active=True,
        )
        tasks.schedule_podcast_feeds()
        mock_sync_podcast_feed.assert_called()

    def test_schedule_podcast_feeds_none_scheduled(self, db, mock_sync_podcast_feed):

        PodcastFactory(
            frequency=None,
            pub_date=None,
            active=True,
        )
        tasks.schedule_podcast_feeds()
        mock_sync_podcast_feed.assert_not_called()


class TestSyncInfreqentPodcastFeedsTests:
    @pytest.fixture
    def mock_sync_podcast_feed(self, mocker):
        return mocker.patch(
            "jcasts.podcasts.tasks.sync_podcast_feed.delay",
            autospec=True,
        )

    def test_sync_infrequent_podcast_feeds(self, db, mock_sync_podcast_feed):
        now = timezone.now()

        podcast = PodcastFactory(
            pub_date=(now - timedelta(days=210)),
            active=True,
        )
        tasks.sync_infrequent_podcast_feeds()

        mock_sync_podcast_feed.assert_called_with(podcast.rss)


class TestSyncPodcastFeed:
    @pytest.fixture
    def mock_parse_feed(self, mocker):
        return mocker.patch(
            "jcasts.podcasts.tasks.parse_feed",
            autospec=True,
        )

    @pytest.fixture
    def mock_sync_podcast_feed(self, mocker):
        return mocker.patch(
            "jcasts.podcasts.tasks.sync_podcast_feed.apply_async",
            autospec=True,
        )

    def test_ok(self, db, mocker, mock_parse_feed, mock_sync_podcast_feed):
        now = timezone.now()
        podcast = PodcastFactory(
            frequency=timedelta(days=1),
            pub_date=now - timedelta(days=3),
        )
        mocker.patch("jcasts.podcasts.tasks.cache.set", return_value=True)
        tasks.sync_podcast_feed(podcast.rss)
        mock_parse_feed.assert_called_with(podcast, force_update=False)
        mock_sync_podcast_feed.assert_called()

    def test_cached(self, db, mocker, mock_parse_feed, mock_sync_podcast_feed):
        now = timezone.now()
        podcast = PodcastFactory(
            frequency=timedelta(days=1),
            pub_date=now - timedelta(days=3),
        )
        mocker.patch("jcasts.podcasts.tasks.cache.set", return_value=False)
        tasks.sync_podcast_feed(podcast.rss)
        mock_parse_feed.assert_not_called()
        mock_sync_podcast_feed.assert_not_called()

    def test_no_next_scheduled(
        self, db, mocker, mock_parse_feed, mock_sync_podcast_feed
    ):
        now = timezone.now()
        podcast = PodcastFactory(
            frequency=None,
            pub_date=now - timedelta(days=3),
        )
        mocker.patch("jcasts.podcasts.tasks.cache.set", return_value=True)
        tasks.sync_podcast_feed(podcast.rss)
        mock_parse_feed.assert_called_with(podcast, force_update=False)
        mock_sync_podcast_feed.assert_not_called()

    def test_does_not_exist(self, db, mocker, mock_parse_feed, mock_sync_podcast_feed):
        mocker.patch("jcasts.podcasts.tasks.cache.set", return_value=True)
        tasks.sync_podcast_feed(1234)
        mock_parse_feed.assert_not_called()
        mock_sync_podcast_feed.assert_not_called()
