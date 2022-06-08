from datetime import timedelta

from django.utils import timezone

from radiofeed.episodes.factories import EpisodeFactory
from radiofeed.podcasts import scheduler
from radiofeed.podcasts.factories import PodcastFactory


class TestSchedulePodcastFeeds:
    def test_parsed_is_none(self, db):
        PodcastFactory(parsed=None)
        assert scheduler.schedule_podcast_feeds().exists()

    def test_inactive(self, db):
        PodcastFactory(parsed=None, active=False)
        assert not scheduler.schedule_podcast_feeds().exists()

    def test_scheduled(self, db):
        now = timezone.now()
        PodcastFactory(
            pub_date=now - timedelta(hours=3), parsed=now - timedelta(hours=3)
        )
        assert scheduler.schedule_podcast_feeds().exists()

    def test_scheduled_just_parsed(self, db):
        now = timezone.now()
        PodcastFactory(
            pub_date=now - timedelta(hours=3), parsed=now - timedelta(minutes=30)
        )
        assert not scheduler.schedule_podcast_feeds().exists()

    def test_not_scheduled(self, db):
        now = timezone.now()
        PodcastFactory(
            pub_date=timezone.now() - timedelta(minutes=30),
            parsed=now - timedelta(hours=3),
        )
        assert not scheduler.schedule_podcast_feeds().exists()

    def test_scheduled_more_than_30_days_ago(self, db):
        now = timezone.now()
        PodcastFactory(
            pub_date=now - timedelta(days=90), parsed=now - timedelta(days=33)
        )
        assert scheduler.schedule_podcast_feeds().exists()

    def test_not_scheduled_more_than_30_days_ago(self, db):
        now = timezone.now()
        PodcastFactory(
            pub_date=now - timedelta(days=90), parsed=now - timedelta(days=7)
        )
        assert not scheduler.schedule_podcast_feeds().exists()


class TestCalculateUpdateInterval:
    def test_no_pub_dates(self):
        assert scheduler.calculate_update_interval([]) == timedelta(hours=1)

    def test_single_pub_date(self):
        assert (
            scheduler.calculate_update_interval(
                [timezone.now() - timedelta(days=3)]
            ).days
            == 3
        )

    def test_multiple_pub_dates(self):
        now = timezone.now()
        pub_dates = [now - timedelta(days=days) for days in range(1, 12)]
        assert scheduler.calculate_update_interval(pub_dates).days == 1

    def test_should_be_min_one_hour(self):
        now = timezone.now()
        pub_dates = [now - timedelta(minutes=minutes * 30) for minutes in range(1, 12)]
        assert scheduler.calculate_update_interval(pub_dates).total_seconds() == 3600

    def test_should_be_max_30_days(self):
        now = timezone.now()
        pub_dates = [now - timedelta(days=days * 100) for days in range(1, 12)]
        assert scheduler.calculate_update_interval(pub_dates).days == 30


class TestIncrementUpdateInterval:
    def test_increment(self):
        assert (
            scheduler.increment_update_interval(timedelta(hours=1)).total_seconds()
            == 4320
        )

    def test_should_be_max_30_days(self):
        assert scheduler.increment_update_interval(timedelta(days=33)).days == 30


class TestReschedulePodcastFeeds:
    def test_reschedule(self, podcast):
        now = timezone.now()

        for i in range(1, 12):
            EpisodeFactory(podcast=podcast, pub_date=now - timedelta(days=i * 3))

        scheduler.reschedule_podcast_feeds()
        podcast.refresh_from_db()
        assert podcast.update_interval.days == 3
