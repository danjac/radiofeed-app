from datetime import timedelta

import pytest

from django.utils import timezone

from jcasts.podcasts import scheduler


def assert_hours(delta, hours):
    assert delta.total_seconds() / 3600 == pytest.approx(hours, 1.0)


class TestReschedule:
    def test_not_none(self):
        now = timezone.now()
        result = scheduler.reschedule(
            timedelta(hours=24),
            scheduler.DEFAULT_MODIFIER,
            True,
        )
        assert result.modifier == 0.06
        assert result.frequency == timedelta(hours=24)
        assert_hours(result.scheduled - now, 8.4)

    def test_not_active(self):
        result = scheduler.reschedule(
            timedelta(hours=24),
            scheduler.DEFAULT_MODIFIER,
            False,
        )
        assert result.modifier is None
        assert result.frequency is None
        assert result.scheduled is None

    def test_max_scheduled(self):
        now = timezone.now()
        result = scheduler.reschedule(
            timedelta(days=60),
            scheduler.DEFAULT_MODIFIER,
            True,
        )
        assert result.modifier == 0.06
        assert result.frequency == timedelta(days=30)
        assert_hours(result.scheduled - now, 30 * 24)

    def test_max_schedule_modifier(self):
        now = timezone.now()
        result = scheduler.reschedule(
            timedelta(days=60),
            1.0,
            True,
        )
        assert result.frequency == timedelta(days=30)
        assert result.modifier == 1.0
        assert_hours(result.scheduled - now, 30 * 24)

    def test_none(self):
        now = timezone.now()
        result = scheduler.reschedule(None, None, True)
        assert_hours(result.scheduled - now, 3)
        assert result.modifier == 0.06
        assert result.frequency == scheduler.DEFAULT_FREQUENCY


class TestSchedule:
    def test_pub_date_none(self):
        result = scheduler.schedule(None, None, [], True)
        assert result.scheduled is None
        assert result.frequency is None
        assert result.modifier is None

    def test_no_pub_dates(self):
        now = timezone.now()
        result = scheduler.schedule(now, None, [], True)
        assert_hours(result.scheduled - now, 24)
        assert result.frequency == scheduler.DEFAULT_FREQUENCY
        assert result.modifier == scheduler.DEFAULT_MODIFIER

    def test_no_pub_dates_with_freq(self):
        now = timezone.now()
        result = scheduler.schedule(now, timedelta(days=3), [], True)
        assert_hours(result.scheduled - now, 3 * 24)
        assert result.frequency == timedelta(days=3)
        assert result.modifier == scheduler.DEFAULT_MODIFIER

    def test_pub_dates(self):
        now = timezone.now()
        dates = [now - timedelta(days=3 * i) for i in range(1, 6)]
        result = scheduler.schedule(now, None, dates, True)
        assert_hours(result.scheduled - now, 24 * 3)
        assert result.frequency == timedelta(days=3)
        assert result.modifier == scheduler.DEFAULT_MODIFIER

    def test_pub_dates_result_scheduled_lt_now(self):
        now = timezone.now()
        dates = [now - timedelta(days=3 * i) for i in range(1, 6)]
        result = scheduler.schedule(now - timedelta(days=4), None, dates, True)
        assert_hours(result.scheduled - now, 24)
        assert result.frequency == timedelta(days=3)
        assert result.modifier == scheduler.DEFAULT_MODIFIER

    def test_last_pub_date_gt_max_value(self):
        now = timezone.now()
        latest = now - timedelta(days=90)
        dates = [latest] + [latest - timedelta(days=3 * i) for i in range(1, 6)]
        result = scheduler.schedule(now, None, dates, True)
        assert_hours(result.scheduled - now, 24 * 30)
        assert result.frequency == scheduler.DEFAULT_FREQUENCY
        assert result.modifier == scheduler.DEFAULT_MODIFIER

    def test_max_value(self):
        now = timezone.now()
        dates = [now - timedelta(days=33 * i) for i in range(1, 6)]
        result = scheduler.schedule(now, None, dates, True)
        assert_hours(result.scheduled - now, 24 * 30)
        assert result.frequency == scheduler.MAX_FREQUENCY
        assert result.modifier == scheduler.DEFAULT_MODIFIER

    def test_min_value(self):
        now = timezone.now()
        dates = [now - timedelta(hours=1 * i) for i in range(1, 6)]
        result = scheduler.schedule(now, None, dates, True)
        assert_hours(result.scheduled - now, 3)
        assert result.frequency == scheduler.MIN_FREQUENCY
        assert result.modifier == scheduler.DEFAULT_MODIFIER


class TestGetFrequency:
    def test_no_pub_dates(self):
        assert scheduler.get_frequency(None, []).days == 1

    def test_single_date(self):
        diff = timedelta(days=1)
        dt = timezone.now() - diff
        assert scheduler.get_frequency(None, [dt]).days == 1

    def test_multiple_dates(self):
        now = timezone.now()
        dates = [now - timedelta(days=3 * i) for i in range(1, 6)]
        assert scheduler.get_frequency(None, dates).days == 3

    def test_freq_not_none(self):
        now = timezone.now()
        dates = [now - timedelta(days=3 * i) for i in range(1, 6)]
        assert scheduler.get_frequency(timedelta(days=12), dates).days == 12

    def test_max_dates_with_one_date_in_range(self):

        now = timezone.now()
        dates = [
            now - timedelta(days=6),
            now - timedelta(days=30),
            now - timedelta(days=90),
        ]
        assert scheduler.get_frequency(None, dates).days == 24

    def test_dates_outside_threshold(self):

        now = timezone.now()
        dates = [
            now - timedelta(days=90),
            now - timedelta(days=120),
            now - timedelta(days=180),
        ]
        assert scheduler.get_frequency(None, dates).days == 1

    def test_min_dates(self):

        now = timezone.now()
        dates = [
            now - timedelta(hours=1),
            now - timedelta(hours=2),
            now - timedelta(hours=3),
        ]
        assert_hours(scheduler.get_frequency(None, dates), 3)
