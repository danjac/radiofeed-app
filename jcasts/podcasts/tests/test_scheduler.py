from datetime import timedelta

import pytest

from django.utils import timezone

from jcasts.episodes.factories import EpisodeFactory
from jcasts.podcasts import scheduler
from jcasts.podcasts.factories import PodcastFactory
from jcasts.podcasts.models import Podcast


class TestCalcFrequency:
    def test_calc_frequency(self):

        now = timezone.now()

        dates = [
            now - timedelta(days=5, hours=12),
            now - timedelta(days=12, hours=12),
            now - timedelta(days=15, hours=12),
            now - timedelta(days=30, hours=12),
        ]

        assert scheduler.calc_frequency(dates).days == 8

    def test_calc_frequency_if_empty(self):
        assert scheduler.calc_frequency([]) is None


class TestCalcFrequencyFromPodcast:
    def test_calc_frequency(self, podcast):

        now = timezone.now()

        [
            EpisodeFactory(podcast=podcast, pub_date=pub_date)
            for pub_date in (
                now - timedelta(days=5, hours=12),
                now - timedelta(days=12, hours=12),
                now - timedelta(days=15, hours=12),
                now - timedelta(days=30, hours=12),
            )
        ]

        assert scheduler.calc_frequency_from_podcast(podcast).days == 8


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

        EpisodeFactory(podcast=podcast, pub_date=timezone.now() - timedelta(days=3))

        scheduled = podcast.scheduled

        assert scheduler.schedule_podcast_feeds(reset=True) == 1
        assert Podcast.objects.filter(scheduled__isnull=False).count() == 1

        podcast.refresh_from_db()
        assert podcast.scheduled > scheduled


class TestGetNextScheduled:
    def test_get_next_scheduled_no_pub_date(self):
        assert (
            scheduler.get_next_scheduled(
                frequency=timedelta(days=1),
                pub_date=None,
            )
            is None
        )

    def test_get_next_scheduled_no_frequency(self):
        assert (
            scheduler.get_next_scheduled(
                frequency=None,
                pub_date=timezone.now() - timedelta(days=7),
            )
            is None
        )

    def test_get_next_scheduled_frequency_zero(self):
        now = timezone.now()
        scheduled = scheduler.get_next_scheduled(
            frequency=timedelta(seconds=0),
            pub_date=now - timedelta(hours=1),
        )
        assert (scheduled - now).total_seconds() == pytest.approx(3600)

    def test_get_next_scheduled_frequency_lt_one_hour(self):
        now = timezone.now()
        scheduled = scheduler.get_next_scheduled(
            frequency=timedelta(seconds=60),
            pub_date=now - timedelta(hours=1),
        )
        assert (scheduled - now).total_seconds() == pytest.approx(3600)

    def test_get_next_scheduled_lt_now(self):
        now = timezone.now()
        scheduled = scheduler.get_next_scheduled(
            frequency=timedelta(days=30),
            pub_date=now - timedelta(days=90),
        )
        assert (scheduled - now).total_seconds() / (24 * 60 * 60) == pytest.approx(1.5)

    def test_get_next_scheduled_gt_now(self):
        now = timezone.now()
        scheduled = scheduler.get_next_scheduled(
            frequency=timedelta(days=7),
            pub_date=now - timedelta(days=6),
        )
        assert (scheduled - now).days == 1
