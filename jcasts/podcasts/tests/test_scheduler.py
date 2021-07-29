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
    ...


class TestSyncSporadicFeeds:
    ...


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
