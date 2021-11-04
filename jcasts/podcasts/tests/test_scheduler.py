from datetime import timedelta

import pytest

from django.utils import timezone

from jcasts.podcasts import scheduler


class TestIncrFrequency:
    def test_incr_frequency(self):
        freq = timedelta(hours=24)
        assert scheduler.incr_frequency(freq).total_seconds() / 3600 == pytest.approx(
            28.8
        )

    def test_is_none(self):
        assert scheduler.incr_frequency(None).days == 1


class TestCalcFrequency:
    def test_no_pub_dates(self):
        assert scheduler.calc_frequency([]) == scheduler.DEFAULT_FREQUENCY

    def test_single_date(self):
        diff = timedelta(days=1)
        dt = timezone.now() - diff
        assert scheduler.calc_frequency([dt]).days == 1

    def test_multiple_dates(self):
        now = timezone.now()
        dates = [now - timedelta(days=3 * i) for i in range(1, 6)]
        assert scheduler.calc_frequency(dates).days == 3

    def test_max_dates_with_one_date_in_range(self):

        now = timezone.now()
        dates = [
            now - timedelta(days=6),
            now - timedelta(days=30),
            now - timedelta(days=90),
        ]
        assert scheduler.calc_frequency(dates).days == 24

    def test_dates_outside_threshold(self):

        now = timezone.now()
        dates = [
            now - timedelta(days=60),
            now - timedelta(days=90),
            now - timedelta(days=120),
        ]
        assert scheduler.calc_frequency(dates).days == 1

    def test_min_dates(self):

        now = timezone.now()
        dates = [
            now - timedelta(hours=1),
            now - timedelta(hours=2),
            now - timedelta(hours=3),
        ]
        assert scheduler.calc_frequency(dates).total_seconds() / 3600 == pytest.approx(
            1
        )


class TestReschedule:
    def test_pub_date_none(self):
        scheduled = scheduler.reschedule(timedelta(days=1), None)
        assert (scheduled - timezone.now()).total_seconds() / 3600 == pytest.approx(24)

    def test_frequency_zero(self):
        now = timezone.now()
        scheduled = scheduler.reschedule(timedelta(seconds=0), now - timedelta(days=3))
        assert (scheduled - now).days == 1

    def test_pub_date_not_none(self):
        now = timezone.now()
        scheduled = scheduler.reschedule(timedelta(days=7), now - timedelta(days=3))
        assert (scheduled - now).days == 4

    def test_pub_date_before_now(self):
        now = timezone.now()
        scheduled = scheduler.reschedule(timedelta(days=3), now - timedelta(days=7))
        assert (scheduled - now).days == 2

    def test_pub_date_before_now_max_value(self):
        now = timezone.now()
        scheduled = scheduler.reschedule(timedelta(days=90), now - timedelta(days=120))
        assert (scheduled - now).days == 14
