from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.podcasts import scheduler
from radiofeed.podcasts.factories import PodcastFactory


class TestSchedulePodcastsForUpdate:
    def test_parsed_is_null(self, db):
        PodcastFactory(parsed=None)
        assert scheduler.schedule_podcasts_for_update().exists()

    def test_pub_date_is_null(self, db):
        PodcastFactory(parsed=timezone.now() - timedelta(hours=2), pub_date=None)
        assert scheduler.schedule_podcasts_for_update().exists()

    def test_inactive(self, db):
        PodcastFactory(parsed=None, active=False)
        assert not scheduler.schedule_podcasts_for_update().exists()

    def test_scheduled(self, db):
        now = timezone.now()
        PodcastFactory(
            parsed=now - timedelta(hours=1),
            pub_date=now - timedelta(days=7),
            update_interval=timedelta(days=7),
        )
        assert scheduler.schedule_podcasts_for_update().exists()

    def test_not_scheduled(self, db):
        now = timezone.now()

        PodcastFactory(
            parsed=now - timedelta(hours=1),
            pub_date=now - timedelta(days=4),
            update_interval=timedelta(days=7),
        )

        assert not scheduler.schedule_podcasts_for_update().exists()

    def test_scheduled_older_than_one_month(self, db):
        now = timezone.now()
        PodcastFactory(
            parsed=now - timedelta(days=30),
            pub_date=now - timedelta(days=60),
            update_interval=timedelta(days=30),
        )
        assert scheduler.schedule_podcasts_for_update().exists()

    def test_not_scheduled_older_than_one_month(self, db):
        now = timezone.now()
        PodcastFactory(
            parsed=now - timedelta(days=7),
            pub_date=now - timedelta(days=60),
            update_interval=timedelta(days=30),
        )
        assert not scheduler.schedule_podcasts_for_update().exists()


class TestIncrementRefreshInterval:
    def test_increment(self):
        assert scheduler.increment_update_interval(
            timedelta(hours=1)
        ).total_seconds() == pytest.approx(66 * 60)

    def test_increment_past_max(self):
        assert scheduler.increment_update_interval(timedelta(days=30)).days == 14


class TestCalculateRefreshInterval:
    def test_no_dates(self):
        assert scheduler.calculate_update_interval([]) == timedelta(hours=1)

    def test_just_one_date(self):

        assert scheduler.calculate_update_interval([timezone.now()]) == timedelta(
            hours=1
        )

    def test_two_dates(self):
        dt = timezone.now()

        pub_dates = [
            dt - timedelta(days=3),
            dt - timedelta(days=6),
        ]

        assert scheduler.calculate_update_interval(pub_dates).days == 3

    def test_sufficent_dates(self):

        dt = timezone.now()

        pub_dates = [
            dt - timedelta(days=3),
            dt - timedelta(days=6),
            dt - timedelta(days=9),
        ]

        assert scheduler.calculate_update_interval(pub_dates).days == 3

    def test_latest_more_than_90_days(self):

        dt = timezone.now()

        pub_dates = [
            dt - timedelta(days=90),
            dt - timedelta(days=96),
            dt - timedelta(days=100),
        ]

        assert scheduler.calculate_update_interval(pub_dates).days == 14

    def test_latest_more_than_14_days(self):

        dt = timezone.now()

        pub_dates = [
            dt - timedelta(days=30),
            dt - timedelta(days=36),
            dt - timedelta(days=40),
        ]

        assert scheduler.calculate_update_interval(pub_dates).days == 14

    def test_over_max(self):

        dt = timezone.now()

        pub_dates = [
            dt - timedelta(days=33),
            dt - timedelta(days=66),
            dt - timedelta(days=99),
        ]

        assert scheduler.calculate_update_interval(pub_dates).days == 14

    def test_no_diffs(self):

        assert (
            scheduler.calculate_update_interval(
                [timezone.now() - timedelta(days=3)] * 10
            ).total_seconds()
            == 3600
        )
