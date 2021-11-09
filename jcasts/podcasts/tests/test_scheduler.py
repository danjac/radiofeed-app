from datetime import timedelta

import pytest

from django.utils import timezone

from jcasts.podcasts import scheduler


def assert_hours(delta, hours):
    assert delta.total_seconds() / 3600 == pytest.approx(hours)


class TestIncrement:
    def test_not_none(self):
        assert_hours(scheduler.increment(timedelta(hours=24)), 28.8)

    def test_none(self):
        assert scheduler.increment(None) is None


class TestSchedule:
    def test_pub_date_none(self):
        assert scheduler.schedule(None, timedelta(days=7)) is None

    def test_frequency_none(self):
        assert scheduler.schedule(timezone.now(), None) is None

    def test_scheduled_gt_now(self):
        now = timezone.now()
        scheduled = scheduler.schedule(now, timedelta(days=7))
        assert_hours(scheduled - now, 7 * 24)

    def test_scheduled_lt_now(self):
        now = timezone.now()
        scheduled = scheduler.schedule(now - timedelta(days=8), timedelta(days=7))
        assert_hours(scheduled - now, 24)

    def test_scheduled_lt_now_gt_20_days(self):
        now = timezone.now()
        scheduled = scheduler.schedule(now - timedelta(days=30), timedelta(days=20))
        assert_hours(scheduled - now, 10 * 24)

    def test_scheduled_lt_now_gt_30_days(self):
        now = timezone.now()
        scheduled = scheduler.schedule(now - timedelta(days=90), timedelta(days=30))
        assert_hours(scheduled - now, 30 * 24)


class TestGetFrequency:
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
