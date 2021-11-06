from datetime import timedelta

import pytest

from django.utils import timezone

from jcasts.podcasts import scheduler
from jcasts.podcasts.models import Podcast


def assert_hours(delta, hours):
    assert delta.total_seconds() / 3600 == pytest.approx(hours)


class TestReschedule:
    def test_freq_is_none(self):
        podcast = Podcast(frequency=None)
        assert scheduler.reschedule(podcast) is None

    def test_pub_date_and_polled_none(self):
        podcast = Podcast(frequency=timedelta(days=1))
        assert_hours(scheduler.reschedule(podcast) - timezone.now(), 24)

    def test_freq_as_arg(self):
        podcast = Podcast(frequency=None)
        assert_hours(
            scheduler.reschedule(podcast, timedelta(days=1)) - timezone.now(), 24
        )

    def test_pub_date_gt_now(self):
        now = timezone.now()
        podcast = Podcast(
            frequency=timedelta(days=1),
            pub_date=now - timedelta(hours=12),
        )
        assert_hours(scheduler.reschedule(podcast) - now, 12)

    def test_polled_gt_now(self):
        now = timezone.now()
        podcast = Podcast(frequency=timedelta(days=1), polled=now - timedelta(hours=12))
        assert_hours(scheduler.reschedule(podcast) - now, 12)

    def test_pub_date_lt_now_and_polled_gt_now(self):
        now = timezone.now()
        podcast = Podcast(
            frequency=timedelta(days=1),
            pub_date=now - timedelta(days=12),
            polled=now - timedelta(hours=12),
        )
        assert_hours(scheduler.reschedule(podcast) - now, 12)

    def test_pub_date_lt_now_and_polled_lt_now(self):
        now = timezone.now()

        podcast = Podcast(
            frequency=timedelta(days=1),
            pub_date=now - timedelta(days=12),
            polled=now - timedelta(days=12),
        )
        assert_hours(scheduler.reschedule(podcast) - now, 24)


class TestIncrement:
    def test_increment(self):
        freq = timedelta(hours=24)

        assert_hours(scheduler.increment(freq), 28.8)

    def test_is_none(self):
        assert scheduler.increment(None).days == 1


class TestCalcFrequency:
    def test_no_pub_dates(self):
        assert scheduler.get_frequency([]).days == 1

    def test_single_date(self):
        diff = timedelta(days=1)
        dt = timezone.now() - diff
        assert scheduler.get_frequency([dt]).days == 1

    def test_multiple_dates(self):
        now = timezone.now()
        dates = [now - timedelta(days=3 * i) for i in range(1, 6)]
        assert scheduler.get_frequency(dates).days == 3

    def test_max_dates_with_one_date_in_range(self):

        now = timezone.now()
        dates = [
            now - timedelta(days=6),
            now - timedelta(days=30),
            now - timedelta(days=90),
        ]
        assert scheduler.get_frequency(dates).days == 30

    def test_dates_outside_threshold(self):

        now = timezone.now()
        dates = [
            now - timedelta(days=60),
            now - timedelta(days=90),
            now - timedelta(days=120),
        ]
        assert scheduler.get_frequency(dates).days == 30

    def test_min_dates(self):

        now = timezone.now()
        dates = [
            now - timedelta(hours=1),
            now - timedelta(hours=2),
            now - timedelta(hours=3),
        ]
        assert_hours(scheduler.get_frequency(dates), 3)
