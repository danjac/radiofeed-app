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
    def test_podcast_not_scheduled(self, db):
        podcast = PodcastFactory(pub_date=timezone.now(), active=True)
        tasks.schedule_podcast_feeds()
        podcast.refresh_from_db()
        assert podcast.scheduled

    def test_podcast_rescheduled(self, db):
        scheduled = timezone.now()
        podcast = PodcastFactory(pub_date=timezone.now(), scheduled=scheduled)
        tasks.schedule_podcast_feeds()
        podcast.refresh_from_db()
        assert podcast.scheduled != scheduled

    def test_podcast_no_pub_date(self, db):
        podcast = PodcastFactory(pub_date=None)
        tasks.schedule_podcast_feeds()
        podcast.refresh_from_db()
        assert podcast.scheduled is None

    def test_podcast_inactive(self, db):
        podcast = PodcastFactory(pub_date=timezone.now(), active=False)
        tasks.schedule_podcast_feeds()
        podcast.refresh_from_db()
        assert podcast.scheduled is None


class TestSyncPodcastFeedsTests:
    @pytest.fixture
    def mock_sync_podcast_feed(self, mocker):
        return mocker.patch(
            "jcasts.podcasts.tasks.sync_podcast_feed.delay",
            autospec=True,
        )

    @pytest.mark.parametrize(
        "delta,active,do_sync",
        [
            (timedelta(minutes=30), True, False),
            (timedelta(minutes=-30), True, True),
            (timedelta(minutes=-30), False, False),
            (timedelta(minutes=200), True, False),
        ],
    )
    def test_sync_podcast_feeds(
        self, db, mock_sync_podcast_feed, delta, active, do_sync
    ):
        now = timezone.now()

        PodcastFactory(scheduled=now + delta, pub_date=now, active=active)
        tasks.sync_podcast_feeds()

        if do_sync:
            mock_sync_podcast_feed.assert_called()
        else:
            mock_sync_podcast_feed.assert_not_called()


class TestSyncPodcastFeed:
    @pytest.fixture
    def mock_parse_feed(self, mocker):
        return mocker.patch(
            "jcasts.podcasts.tasks.parse_feed",
            autospec=True,
        )

    def test_ok(self, db, podcast, mock_parse_feed):
        tasks.sync_podcast_feed(podcast.id)
        mock_parse_feed.assert_called()

    def test_does_not_exist(self, db, mock_parse_feed):
        tasks.sync_podcast_feed(1234)
        mock_parse_feed.assert_not_called()
