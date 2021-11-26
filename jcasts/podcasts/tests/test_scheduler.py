from datetime import timedelta

import pytest

from django.utils import timezone

from jcasts.podcasts import scheduler
from jcasts.podcasts.models import Podcast


def assert_hours(delta, hours):
    assert delta.total_seconds() / 3600 == pytest.approx(hours, 1.0)


class TestReschedule:
    def test_reschedule(self):
        frequency, modifier = scheduler.reschedule(
            Podcast(frequency=timedelta(hours=24))
        )
        assert_hours(frequency, 24)
        assert modifier == 0.06

    def test_reschedule_past_limit(self):
        frequency, modifier = scheduler.reschedule(
            Podcast(frequency=timedelta(days=30))
        )
        assert_hours(frequency, 24 * 30)
        assert modifier == 0.06

    def test_reschedule_overflow(self):
        frequency, modifier = scheduler.reschedule(
            Podcast(frequency=timedelta(days=30), frequency_modifier=300)
        )
        assert_hours(frequency, 24 * 30)
        assert modifier == 300


class TestSchedule:
    def test_no_pub_dates(self):
        frequency, modifier = scheduler.schedule([])
        assert_hours(frequency, 24)
        assert modifier == 0.05

    def test_single_date(self):
        diff = timedelta(days=1)
        dt = timezone.now() - diff
        frequency, modifier = scheduler.schedule([dt])
        assert_hours(frequency, 24)
        assert modifier == 0.05

    def test_multiple_dates(self):
        now = timezone.now()
        dates = [now - timedelta(days=3 * i) for i in range(1, 6)]
        frequency, modifier = scheduler.schedule(dates)
        assert_hours(frequency, 72)
        assert modifier == 0.05

    def test_new_modifier(self):
        now = timezone.now()
        dates = [now - timedelta(days=3 * i) for i in range(1, 6)]
        frequency, modifier = scheduler.schedule(dates)
        assert_hours(frequency, 72)
        assert modifier == 0.05

    def test_high_variance(self):
        now = timezone.now()

        dates = [
            now - timedelta(days=value)
            for value in [2, 3, 5, 6, 9, 11, 12, 15, 16, 20, 25]
        ]

        frequency, modifier = scheduler.schedule(dates)
        assert_hours(frequency, 54)
        assert modifier == 0.05

    def test_max_dates_with_one_date(self):

        now = timezone.now()
        dates = [
            now - timedelta(days=6),
        ]
        frequency, modifier = scheduler.schedule(dates)
        assert_hours(frequency, 6 * 24)
        assert modifier == 0.05

    def test_max_dates_with_one_date_in_range(self):

        now = timezone.now()
        dates = [
            now - timedelta(days=6),
            now - timedelta(days=30),
            now - timedelta(days=90),
        ]
        frequency, modifier = scheduler.schedule(dates)
        assert_hours(frequency, 24 * 30)
        assert modifier == 0.05

    def test_dates_outside_threshold(self):

        now = timezone.now()
        dates = [
            now - timedelta(days=90),
            now - timedelta(days=120),
            now - timedelta(days=180),
        ]
        frequency, modifier = scheduler.schedule(dates)
        assert_hours(frequency, 24 * 30)
        assert modifier == 0.05

    def test_min_dates(self):

        now = timezone.now()
        dates = [
            now - timedelta(hours=1),
            now - timedelta(hours=2),
            now - timedelta(hours=3),
        ]
        frequency, modifier = scheduler.schedule(dates)
        assert_hours(frequency, 3)
        assert modifier == 0.05
