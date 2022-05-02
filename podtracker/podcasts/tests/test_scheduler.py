from datetime import timedelta

import pytest

from django.utils import timezone

from podtracker.podcasts import scheduler
from podtracker.podcasts.factories import PodcastFactory, SubscriptionFactory
from podtracker.podcasts.models import Podcast


class TestSchedulePodcastFeeds:
    @pytest.mark.parametrize(
        "pub_date,after,before,success",
        [
            (None, None, None, True),
            (None, timedelta(days=14), None, True),
            (None, None, timedelta(days=7), True),
            (timedelta(days=7), None, None, True),
            (timedelta(days=7), timedelta(days=14), None, True),
            (timedelta(days=30), timedelta(days=14), None, False),
            (timedelta(days=7), timedelta(days=14), timedelta(hours=3), True),
            (timedelta(days=7), timedelta(days=14), timedelta(days=10), False),
            (timedelta(days=30), None, timedelta(days=14), True),
            (timedelta(days=9), None, timedelta(days=14), False),
        ],
    )
    def test_time_values(
        self,
        db,
        pub_date,
        after,
        before,
        success,
    ):

        now = timezone.now()

        podcast = PodcastFactory(pub_date=now - pub_date if pub_date else None)

        podcast_ids = scheduler.schedule_podcast_feeds(
            Podcast.objects.all(), after=after, before=before
        )
        count = len(podcast_ids)

        assert Podcast.objects.filter(queued__isnull=False).exists() is success, (
            pub_date,
            after,
            before,
            success,
        )

        if success:
            assert count == 1
            assert podcast.id in podcast_ids
        else:
            assert count == 0

    @pytest.mark.parametrize(
        "active,success",
        [
            (True, True),
            (False, False),
        ],
    )
    def test_active(self, db, active, success):

        podcast = PodcastFactory(active=active, promoted=True, pub_date=timezone.now())

        podcast_ids = scheduler.schedule_podcast_feeds(Podcast.objects.all())
        count = len(podcast_ids)

        Podcast.objects.filter(queued__isnull=False).exists() is success

        if success:
            assert count == 1
            assert podcast.id in podcast_ids
        else:
            assert count == 0

    @pytest.mark.parametrize(
        "queued,success",
        [
            (False, True),
            (True, False),
        ],
    )
    def test_queued(self, db, queued, success):
        podcast = PodcastFactory(
            queued=timezone.now() if queued else None, promoted=True
        )

        podcast_ids = scheduler.schedule_podcast_feeds(Podcast.objects.all())
        count = len(podcast_ids)

        if success:
            assert count == 1
            assert podcast.id in podcast_ids
        else:
            assert count == 0


class TestSchedulePrimaryFeeds:
    @pytest.mark.parametrize(
        "promoted,subscribed,success",
        [
            (True, True, True),
            (True, False, True),
            (False, True, True),
            (False, False, False),
        ],
    )
    def test_promoted_or_subscribed(
        self,
        db,
        promoted,
        subscribed,
        success,
    ):

        podcast = PodcastFactory(promoted=promoted)

        if subscribed:
            SubscriptionFactory(podcast=podcast)

        podcast_ids = scheduler.schedule_primary_feeds()
        count = len(podcast_ids)

        Podcast.objects.filter(queued__isnull=False).exists() is success

        if success:
            assert count == 1
            assert podcast.id in podcast_ids
        else:
            assert count == 0


class TestScheduleSecondaryFeeds:
    @pytest.mark.parametrize(
        "promoted,subscribed,success",
        [
            (True, True, False),
            (True, False, False),
            (False, True, False),
            (False, False, True),
        ],
    )
    def test_promoted_or_subscribed(
        self,
        db,
        promoted,
        subscribed,
        success,
    ):

        podcast = PodcastFactory(promoted=promoted, pub_date=None)

        if subscribed:
            SubscriptionFactory(podcast=podcast)

        podcast_ids = scheduler.schedule_secondary_feeds()
        count = len(podcast_ids)

        Podcast.objects.filter(queued__isnull=False).exists() is success

        if success:
            assert count == 1
            assert podcast.id in podcast_ids
        else:
            assert count == 0
