from datetime import timedelta

import pytest
import pytz

from django.utils import timezone

from jcasts.episodes.factories import EpisodeFactory
from jcasts.podcasts import scheduler
from jcasts.podcasts.factories import PodcastFactory
from jcasts.podcasts.models import Podcast


class TestGetFrequency:
    def test_get_frequency(self):

        now = timezone.now()

        dates = [
            now - timedelta(days=5, hours=12),
            now - timedelta(days=8, hours=12),
            now - timedelta(days=11, hours=12),
            now - timedelta(days=15, hours=12),
            now - timedelta(days=18, hours=12),
            now - timedelta(days=21, hours=12),
        ]

        assert scheduler.get_frequency(dates).days == 1

    def test_get_frequency_gt_week(self):
        """Max should be 7 days"""

        now = timezone.now()

        dates = [
            now - timedelta(days=5, hours=12),
            now - timedelta(days=12, hours=12),
            now - timedelta(days=15, hours=12),
            now - timedelta(days=30, hours=12),
            now - timedelta(days=45, hours=12),
            now - timedelta(days=60, hours=12),
        ]

        # actual value ~11 days
        assert scheduler.get_frequency(dates).days == 7

    def test_get_frequency_insufficient_dates(self):

        assert (
            scheduler.get_frequency(
                [
                    timezone.now() - timedelta(days=5, hours=12),
                ],
            )
            is None
        )

    def test_get_frequency_not_utc(self):
        now = timezone.now()
        dts = [now - timedelta(days=i * 5, hours=12) for i in range(3)]

        dts = [pytz.timezone("Europe/Helsinki").normalize(dt) for dt in dts]

        assert scheduler.get_frequency(dts).days == 1

    def test_get_frequency_if_empty(self):
        assert scheduler.get_frequency([]) is None


class TestSchedulePodcastFeeds:
    @pytest.mark.parametrize(
        "is_scheduled,last_pub,freq,active,result,num_scheduled",
        [
            (False, timedelta(days=30), timedelta(days=7), True, 1, 1),
            (True, timedelta(days=30), timedelta(days=7), True, 1, 1),
            (False, timedelta(days=30), None, True, 1, 1),
            (False, timedelta(days=99), timedelta(days=7), True, 1, 1),
            (False, None, timedelta(days=7), True, 0, 0),
        ],
    )
    def test_schedule(
        self, db, is_scheduled, last_pub, freq, active, result, num_scheduled
    ):
        now = timezone.now()

        podcast = PodcastFactory(
            scheduled=now if is_scheduled else None,
            pub_date=now - last_pub if last_pub else None,
            active=active,
        )

        if freq:
            EpisodeFactory(pub_date=now - freq, podcast=podcast)

        assert scheduler.schedule_podcast_feeds() == result
        assert Podcast.objects.filter(scheduled__isnull=False).count() == num_scheduled


class TestSchedule:
    def test_schedule_no_pub_date(self, db):
        assert (
            scheduler.schedule(
                PodcastFactory(pub_date=None), self.get_pub_dates(3, 6, 9)
            )
            is None
        )

    def test_schedule_inactive(self, db):
        assert (
            scheduler.schedule(
                PodcastFactory(active=False), self.get_pub_dates(3, 6, 9)
            )
            is None
        )

    def test_schedule_no_recent_pub_dates(self, db):
        now = timezone.now()
        scheduled = scheduler.schedule(
            PodcastFactory(active=True, pub_date=now - timedelta(days=120)),
            [],
        )

        assert round((scheduled - now).total_seconds() / 3600) == 144

    def test_schedule_frequency_zero(self, podcast):
        now = timezone.now()
        scheduled = scheduler.schedule(
            PodcastFactory(),
            [now - timedelta(hours=1)],
        )
        assert round((scheduled - now).total_seconds()) == pytest.approx(3600, rel=10)

    def test_schedule_frequency_lt_one_hour(self, db):
        now = timezone.now()

        scheduled = scheduler.schedule(
            PodcastFactory(),
            [
                now - timedelta(minutes=30),
                now - timedelta(minutes=30),
                now - timedelta(minutes=30),
                now - timedelta(minutes=30),
                now - timedelta(minutes=30),
                now - timedelta(minutes=30),
            ],
        )
        assert round((scheduled - now).total_seconds()) == pytest.approx(3600, rel=10)

    def test_schedule_frequency_less_than_one_week(self, db):
        now = timezone.now()

        scheduled = scheduler.schedule(
            PodcastFactory(), [now - timedelta(days=7 * i) for i in range(1, 8)]
        )
        assert round((scheduled - now).total_seconds() / 3600) == 24

    def test_schedule_lt_now(self, db):
        now = timezone.now()
        scheduled = scheduler.schedule(
            PodcastFactory(), self.get_pub_dates(3, 6, 9, 12, 15, 18)
        )
        assert (scheduled - now).days == 1

    def test_schedule_from_episodes(self, podcast):
        now = timezone.now()

        [
            EpisodeFactory(podcast=podcast, pub_date=pub_date)
            for pub_date in self.get_pub_dates(3, 6, 9, 12, 15, 18)
        ]
        scheduled = scheduler.schedule(podcast)
        assert round((scheduled - now).total_seconds() / 3600) == 24

    def test_schedule_from_episodes_over_threshold(self, db):
        now = timezone.now()
        podcast = PodcastFactory(pub_date=now - timedelta(days=100))

        [
            EpisodeFactory(podcast=podcast, pub_date=pub_date)
            for pub_date in self.get_pub_dates(100, 120, 180)
        ]

        scheduled = scheduler.schedule(podcast)
        assert round((scheduled - now).total_seconds() / 3600) == 120

    def get_pub_dates(self, *days):
        now = timezone.now()
        return [now - timedelta(days=day) for day in days]
