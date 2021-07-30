from datetime import timedelta

import pytest

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
            now - timedelta(days=12, hours=12),
            now - timedelta(days=15, hours=12),
            now - timedelta(days=30, hours=12),
        ]

        assert scheduler.get_frequency(dates).days == 8

    def test_get_frequency_if_empty(self):
        assert scheduler.get_frequency([]) is None


class TestSchedulePodcastFeeds:
    @pytest.mark.parametrize(
        "is_scheduled,last_pub,freq,active,result,num_scheduled",
        [
            (False, timedelta(days=30), timedelta(days=7), True, 1, 1),
            (True, timedelta(days=30), timedelta(days=7), True, 0, 1),
            (False, timedelta(days=30), None, True, 1, 0),
            (False, timedelta(days=99), timedelta(days=7), True, 0, 0),
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

    def test_schedule_reset(self, db):
        now = timezone.now()

        podcast = PodcastFactory(
            scheduled=now - timedelta(days=10),
            pub_date=now - timedelta(days=30),
            active=True,
        )

        EpisodeFactory(podcast=podcast, pub_date=timezone.now() - timedelta(days=3))

        scheduled = podcast.scheduled

        assert scheduler.schedule_podcast_feeds(reset=True) == 1
        assert Podcast.objects.filter(scheduled__isnull=False).count() == 1

        podcast.refresh_from_db()
        assert podcast.scheduled > scheduled


class TestSchedule:
    def test_schedule_no_pub_date(self, podcast):
        assert scheduler.schedule(PodcastFactory(pub_date=None)) is None

    def test_schedule_frequency_zero(self, podcast):
        now = timezone.now()
        scheduled = scheduler.schedule(
            PodcastFactory(),
            [now - timedelta(hours=1)],
        )
        assert (scheduled - now).total_seconds() == pytest.approx(3600)

    def test_schedule_frequency_lt_one_hour(self, db):
        now = timezone.now()

        scheduled = scheduler.schedule(
            PodcastFactory(),
            [now - timedelta(seconds=60)],
        )
        assert (scheduled - now).total_seconds() == pytest.approx(3600)

    def test_schedule_lt_now(self, db):
        now = timezone.now()
        scheduled = scheduler.schedule(
            PodcastFactory(),
            [
                now - timedelta(days=3),
                now - timedelta(days=6),
                now - timedelta(days=9),
            ],
        )
        assert (scheduled - now).days == 3

    def test_schedule_from_episodes(self, podcast):
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

        scheduled = scheduler.schedule(podcast)
        assert (scheduled - now).days == 7
