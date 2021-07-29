from datetime import timedelta

import pytest

from django.utils import timezone

from jcasts.podcasts import scheduler
from jcasts.podcasts.factories import PodcastFactory
from jcasts.podcasts.models import Podcast


class TestSchedulePodcastFeeds:
    @pytest.mark.parametrize(
        "is_scheduled,last_pub,freq,active,result,num_scheduled",
        [
            (False, timedelta(days=30), timedelta(days=7), True, 1, 1),
            (True, timedelta(days=30), timedelta(days=7), True, 0, 1),
            (False, timedelta(days=30), None, False, 0, 0),
            (False, timedelta(days=99), timedelta(days=7), True, 0, 0),
            (False, None, timedelta(days=7), True, 0, 0),
        ],
    )
    def test_schedule(
        self, db, is_scheduled, last_pub, freq, active, result, num_scheduled
    ):
        now = timezone.now()
        PodcastFactory(
            scheduled=now if is_scheduled else None,
            pub_date=now - last_pub if last_pub else None,
            frequency=freq,
            active=active,
        )

        assert scheduler.schedule_podcast_feeds() == result
        assert Podcast.objects.filter(scheduled__isnull=False).count() == num_scheduled

    def test_schedule_reset(self, db):
        now = timezone.now()
        podcast = PodcastFactory(
            scheduled=now - timedelta(days=10),
            frequency=timedelta(days=7),
            active=True,
        )

        scheduled = podcast.scheduled

        assert scheduler.schedule_podcast_feeds(reset=True) == 1
        assert Podcast.objects.filter(scheduled__isnull=False).count() == 1

        podcast.refresh_from_db()
        assert podcast.scheduled > scheduled


class TestSyncFrequentFeeds:
    @pytest.fixture
    def mock_sync_podcast_feed(self, mocker):
        return mocker.patch("jcasts.podcasts.scheduler.sync_podcast_feed.delay")

    @pytest.mark.parametrize(
        "force_update,active,scheduled,last_pub,result",
        [
            (False, True, timedelta(hours=-1), timedelta(days=30), 1),
            (False, True, timedelta(hours=1), timedelta(days=30), 0),
            (True, True, timedelta(hours=1), timedelta(days=30), 1),
            (False, False, timedelta(hours=-1), timedelta(days=30), 0),
            (False, False, None, timedelta(days=30), 0),
            (False, True, timedelta(hours=-1), timedelta(days=99), 0),
            (True, True, timedelta(hours=-1), timedelta(days=99), 0),
        ],
    )
    def test_sync_frequent_feeds(
        self,
        db,
        mock_sync_podcast_feed,
        force_update,
        active,
        scheduled,
        last_pub,
        result,
    ):
        now = timezone.now()
        PodcastFactory(
            active=active,
            scheduled=now + scheduled if scheduled else None,
            pub_date=now - last_pub if last_pub else None,
        )
        assert scheduler.sync_frequent_feeds(force_update=force_update) == result

        if result:
            mock_sync_podcast_feed.assert_called()
        else:
            mock_sync_podcast_feed.assert_not_called()


class TestSyncSporadicFeeds:
    @pytest.fixture
    def mock_sync_podcast_feed(self, mocker):
        return mocker.patch("jcasts.podcasts.scheduler.sync_podcast_feed.delay")

    @pytest.mark.parametrize(
        "active,last_pub,result",
        [
            (True, timedelta(days=105), 1),
            (True, timedelta(days=99), 0),
            (True, timedelta(days=30), 0),
            (True, None, 0),
            (False, timedelta(days=99), 0),
        ],
    )
    def test_sync_sporadic_feeds(
        self, db, mock_sync_podcast_feed, active, last_pub, result
    ):
        PodcastFactory(
            active=active,
            pub_date=timezone.now() - last_pub if last_pub else None,
        )
        assert scheduler.sync_sporadic_feeds() == result

        if result:
            mock_sync_podcast_feed.assert_called()
        else:
            mock_sync_podcast_feed.assert_not_called()


class TestSyncPodcastFeed:
    @pytest.fixture
    def mock_parse_feed(self, mocker):
        return mocker.patch("jcasts.podcasts.scheduler.parse_feed")

    def test_sync_podcast_feed(self, podcast, mock_parse_feed):
        scheduler.sync_podcast_feed.delay(podcast.rss)
        mock_parse_feed.assert_called()

    def test_sync_podcast_feed_does_not_exist(self, db, mock_parse_feed):
        scheduler.sync_podcast_feed.delay("https://example.com/rss.xml")
        mock_parse_feed.assert_not_called()
