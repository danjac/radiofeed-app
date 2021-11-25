from datetime import timedelta

import pytest

from django.utils import timezone

from jcasts.podcasts import scheduler


def assert_hours(delta, hours):
    assert delta.total_seconds() / 3600 == pytest.approx(hours, 1.0)


class TestGetFrequency:
    def test_no_pub_dates(self):
        assert_hours(scheduler.schedule([]), 8)

    def test_single_date(self):
        diff = timedelta(days=1)
        dt = timezone.now() - diff
        assert_hours(scheduler.schedule([dt]), 8)

    def test_multiple_dates(self):
        now = timezone.now()
        dates = [now - timedelta(days=3 * i) for i in range(1, 6)]
        assert_hours(scheduler.schedule(dates), 24)

    def test_high_variance(self):
        now = timezone.now()

        dates = [
            now - timedelta(days=value)
            for value in [2, 3, 5, 6, 9, 11, 12, 15, 16, 20, 25]
        ]

        assert_hours(scheduler.schedule(dates), 24)

    def test_max_dates_with_one_date(self):

        now = timezone.now()
        dates = [
            now - timedelta(days=6),
        ]
        assert_hours(scheduler.schedule(dates), 24)

    def test_max_dates_with_one_date_in_range(self):

        now = timezone.now()
        dates = [
            now - timedelta(days=6),
            now - timedelta(days=30),
            now - timedelta(days=90),
        ]
        assert_hours(scheduler.schedule(dates), 48)

    def test_dates_outside_threshold(self):

        now = timezone.now()
        dates = [
            now - timedelta(days=90),
            now - timedelta(days=120),
            now - timedelta(days=180),
        ]
        assert_hours(scheduler.schedule(dates), 48)

    def test_min_dates(self):

        now = timezone.now()
        dates = [
            now - timedelta(hours=1),
            now - timedelta(hours=2),
            now - timedelta(hours=3),
        ]
        assert_hours(scheduler.schedule(dates), 3)
