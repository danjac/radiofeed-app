from datetime import timedelta

import pytest

from django.utils import timezone

from jcasts.podcasts import scheduler


def assert_hours(delta, hours):
    assert delta.total_seconds() / 3600 == pytest.approx(hours, 1.0)


class TestReschedule:
    def test_not_none(self):
        now = timezone.now()
        scheduled, frequency, modifier = scheduler.reschedule(
            timedelta(hours=24),
            scheduler.DEFAULT_MODIFIER,
        )
        assert modifier == 0.06
        assert frequency == timedelta(hours=24)
        assert_hours(scheduled - now, 8.4)

    def test_max_scheduled(self):
        now = timezone.now()
        scheduled, frequency, modifier = scheduler.reschedule(
            timedelta(days=60), scheduler.DEFAULT_MODIFIER
        )
        assert modifier == 0.06
        assert frequency == timedelta(days=60)
        assert_hours(scheduled - now, 30 * 24)

    def test_max_schedule_modifier(self):
        now = timezone.now()
        scheduled, frequency, modifier = scheduler.reschedule(timedelta(days=60), 1.0)
        assert frequency == timedelta(days=60)
        assert modifier == 1.0
        assert_hours(scheduled - now, 30 * 24)

    def test_none(self):
        now = timezone.now()
        scheduled, frequency, modifier = scheduler.reschedule(None, None)
        assert_hours(scheduled - now, 3)
        assert modifier == 0.06
        assert frequency == scheduler.DEFAULT_FREQUENCY


class TestSchedule:
    def test_no_pub_dates(self):
        now = timezone.now()
        scheduled, frequency, modifier = scheduler.schedule(now, [])
        assert_hours(scheduled - now, 24)
        assert frequency == scheduler.DEFAULT_FREQUENCY
        assert modifier == scheduler.DEFAULT_MODIFIER

    def test_no_pub_dates_with_freq(self):
        now = timezone.now()
        scheduled, frequency, modifier = scheduler.schedule(now, [])
        assert_hours(scheduled - now, 3 * 24)
        assert frequency == timedelta(days=1)
        assert modifier == scheduler.DEFAULT_MODIFIER

    def test_pub_dates(self):
        now = timezone.now()
        dates = [now - timedelta(days=3 * i) for i in range(1, 6)]
        scheduled, frequency, modifier = scheduler.schedule(now, dates)
        assert_hours(scheduled - now, 24 * 3)
        assert frequency == timedelta(days=3)
        assert modifier == scheduler.DEFAULT_MODIFIER

    def test_pub_dates_result_scheduled_lt_now(self):
        now = timezone.now()
        dates = [now - timedelta(days=7 * i) for i in range(1, 6)]
        scheduled, frequency, modifier = scheduler.schedule(
            now - timedelta(days=8), dates
        )
        assert_hours(scheduled - now, 24)
        assert frequency == timedelta(days=7)
        assert modifier == scheduler.DEFAULT_MODIFIER

    def test_last_pub_date_gt_max_value(self):
        now = timezone.now()
        latest = now - timedelta(days=90)
        dates = [latest] + [latest - timedelta(days=3 * i) for i in range(1, 6)]
        scheduled, frequency, modifier = scheduler.schedule(now, dates)
        assert_hours(scheduled - now, 24 * 30)
        assert frequency == scheduler.DEFAULT_FREQUENCY
        assert modifier == scheduler.DEFAULT_MODIFIER

    def test_max_value(self):
        now = timezone.now()
        dates = [now - timedelta(days=33 * i) for i in range(1, 6)]
        scheduled, frequency, modifier = scheduler.schedule(now, dates)
        assert_hours(scheduled - now, 24 * 30)
        assert frequency == scheduler.MAX_FREQUENCY
        assert modifier == scheduler.DEFAULT_MODIFIER

    def test_min_value(self):
        now = timezone.now()
        dates = [now - timedelta(hours=1 * i) for i in range(1, 6)]
        scheduled, frequency, modifier = scheduler.schedule(now, dates)
        assert_hours(scheduled - now, 3)
        assert frequency == scheduler.MIN_FREQUENCY
        assert modifier == scheduler.DEFAULT_MODIFIER


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

    def test_high_variance(self):
        now = timezone.now()

        dates = [
            now - timedelta(days=value)
            for value in [2, 3, 5, 6, 9, 11, 12, 15, 16, 20, 25]
        ]

        for _ in range(1000):
            freq = scheduler.get_frequency(dates)
            hours = round(freq.total_seconds() / 3600)
            assert hours in range(48, 60)

    def test_max_dates_with_one_date_in_range(self):

        now = timezone.now()
        dates = [
            now - timedelta(days=6),
            now - timedelta(days=30),
            now - timedelta(days=90),
        ]
        assert scheduler.get_frequency(dates).days == 14

    def test_dates_outside_threshold(self):

        now = timezone.now()
        dates = [
            now - timedelta(days=90),
            now - timedelta(days=120),
            now - timedelta(days=180),
        ]
        assert scheduler.get_frequency(dates).days == 1

    def test_min_dates(self):

        now = timezone.now()
        dates = [
            now - timedelta(hours=1),
            now - timedelta(hours=2),
            now - timedelta(hours=3),
        ]
        assert_hours(scheduler.get_frequency(dates), 3)
