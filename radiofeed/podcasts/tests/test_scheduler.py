from datetime import datetime, timedelta

from django.utils import timezone

from radiofeed.podcasts import scheduler
from radiofeed.podcasts.factories import PodcastFactory, SubscriptionFactory


class TestSchedulePodcastsForUpdate:
    def test_parsed_is_null(self, db):
        PodcastFactory(parsed=None)
        assert scheduler.schedule_podcasts_for_update().exists()

    def test_inactive(self, db):
        PodcastFactory(parsed=None, active=False)
        assert not scheduler.schedule_podcasts_for_update().exists()

    def test_scheduled(self, db):
        PodcastFactory(parsed=timezone.now() - timedelta(hours=1))
        assert scheduler.schedule_podcasts_for_update().exists()

    def test_not_scheduled(self, db):
        PodcastFactory(parsed=timezone.now() - timedelta(minutes=30))
        assert not scheduler.schedule_podcasts_for_update().exists()

    def test_promoted_scheduled(self, db):
        PodcastFactory(parsed=timezone.now() - timedelta(hours=1), promoted=True)
        assert scheduler.schedule_podcasts_for_update().exists()

    def test_promoted_not_scheduled(self, db):
        PodcastFactory(parsed=timezone.now() - timedelta(minutes=30), promoted=True)
        assert not scheduler.schedule_podcasts_for_update().exists()

    def test_subscribed_scheduled(self, db):
        SubscriptionFactory(podcast__parsed=timezone.now() - timedelta(hours=1))
        assert scheduler.schedule_podcasts_for_update().exists()

    def test_subscribed_not_scheduled(self, db):
        SubscriptionFactory(podcast__parsed=timezone.now() - timedelta(minutes=30))
        assert not scheduler.schedule_podcasts_for_update().exists()


class TestIncrementRefreshInterval:
    def test_increment(self):
        assert scheduler.increment_refresh_interval(timedelta(hours=1)) == timedelta(
            hours=1, minutes=6
        )

    def test_increment_past_maximum(self):
        assert scheduler.increment_refresh_interval(timedelta(hours=24)) == timedelta(
            hours=24
        )


class TestCalculateRefreshInterval:
    def test_no_dates(self):
        assert scheduler.calculate_refresh_interval([]) == timedelta(hours=1)

    def test_just_one_date(self):

        assert scheduler.calculate_refresh_interval(
            [datetime(year=2022, month=6, day=1)]
        ) == timedelta(hours=1)

    def test_two_dates(self):
        dt = datetime(year=2022, month=6, day=1)

        pub_dates = [
            dt,
            dt - timedelta(days=3),
        ]

        assert scheduler.calculate_refresh_interval(pub_dates) == timedelta(days=3)

    def test_sufficent_dates(self):

        dt = datetime(year=2022, month=6, day=1)

        pub_dates = [
            dt,
            dt - timedelta(days=3),
            dt - timedelta(days=6),
        ]

        assert scheduler.calculate_refresh_interval(pub_dates) == timedelta(days=3)
