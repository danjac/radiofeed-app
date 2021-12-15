from datetime import timedelta

import pytest

from django.utils import timezone

from jcasts.podcasts import scheduler
from jcasts.podcasts.factories import FeedFactory, FollowFactory, PodcastFactory
from jcasts.podcasts.models import Podcast
from jcasts.podcasts.rss_parser import Feed


@pytest.fixture
def feed():
    return Feed(**FeedFactory())


class TestEmptyQueue:
    def test_empty_queue(self, db, mock_feed_queue):

        podcast = PodcastFactory(queued=timezone.now(), feed_queue="feeds")
        mock_feed_queue.enqueued.append(podcast.id)

        scheduler.empty_queue("feeds")

        assert podcast.id not in mock_feed_queue.enqueued
        podcast.refresh_from_db()

        assert podcast.feed_queue is None
        assert podcast.queued is None

    def test_empty_all_queues(self, db, mock_feed_queue):

        podcast = PodcastFactory(queued=timezone.now(), feed_queue="feeds")
        mock_feed_queue.enqueued.append(podcast.id)

        scheduler.empty_all_queues()

        assert podcast.id not in mock_feed_queue.enqueued
        podcast.refresh_from_db()

        assert podcast.feed_queue is None
        assert podcast.queued is None


class TestEnqueue:
    def test_enqueue_one(self, db, mock_feed_queue, podcast):

        scheduler.enqueue(podcast.id)
        assert podcast.id in mock_feed_queue.enqueued
        assert (
            Podcast.objects.filter(
                queued__isnull=False, feed_queue__isnull=False
            ).exists()
            is True
        )

    def test_enqueue_many(self, db, mock_feed_queue, podcast):

        scheduler.enqueue(*[podcast.id])
        assert podcast.id in mock_feed_queue.enqueued
        assert (
            Podcast.objects.filter(
                queued__isnull=False, feed_queue__isnull=False
            ).exists()
            is True
        )

    def test_empty(self, db, mock_feed_queue):

        scheduler.enqueue(*[])

        assert not mock_feed_queue.enqueued
        assert (
            Podcast.objects.filter(
                queued__isnull=False, feed_queue__isnull=False
            ).exists()
            is False
        )


class TestSchedulePrimaryFeeds:
    @pytest.mark.parametrize(
        "active,success",
        [
            (True, True),
            (False, False),
        ],
    )
    def test_active(self, db, mock_feed_queue, active, success):

        podcast = PodcastFactory(active=active, promoted=True)

        scheduler.schedule_primary_feeds()

        Podcast.objects.filter(queued__isnull=False).exists() is success

        if success:
            assert podcast.id in mock_feed_queue.enqueued
        else:
            assert podcast.id not in mock_feed_queue.enqueued

    @pytest.mark.parametrize(
        "promoted,followed,success",
        [
            (True, True, True),
            (True, False, True),
            (False, True, True),
            (False, False, False),
        ],
    )
    def test_promoted_or_followed(
        self,
        db,
        mock_feed_queue,
        promoted,
        followed,
        success,
    ):

        podcast = PodcastFactory(promoted=promoted)

        if followed:
            FollowFactory(podcast=podcast)

        scheduler.schedule_primary_feeds()

        Podcast.objects.filter(queued__isnull=False).exists() is success

        if success:
            assert podcast.id in mock_feed_queue.enqueued
        else:
            assert podcast.id not in mock_feed_queue.enqueued

    @pytest.mark.parametrize(
        "queued,success",
        [
            (False, True),
            (True, False),
        ],
    )
    def test_queued(self, db, mock_feed_queue, queued, success):
        podcast = PodcastFactory(
            queued=timezone.now() if queued else None, promoted=True
        )

        scheduler.schedule_primary_feeds()

        if success:
            assert podcast.id in mock_feed_queue.enqueued
        else:
            assert podcast.id not in mock_feed_queue.enqueued


class TestScheduleSecondaryFeeds:
    @pytest.mark.parametrize(
        "pub_date,after,before,success",
        [
            (None, None, None, True),
            (None, timedelta(days=14), None, True),
            (timedelta(days=30), timedelta(days=14), None, False),
            (timedelta(days=30), None, timedelta(days=14), True),
            (timedelta(days=9), None, timedelta(days=14), False),
        ],
    )
    def test_time_values(
        self,
        db,
        mock_feed_queue,
        pub_date,
        after,
        before,
        success,
    ):

        now = timezone.now()

        podcast = PodcastFactory(
            pub_date=now - pub_date if pub_date else None,
        )

        scheduler.schedule_secondary_feeds(after=after, before=before)
        assert Podcast.objects.filter(queued__isnull=False).exists() is success

        if success:
            assert podcast.id in mock_feed_queue.enqueued
        else:
            assert podcast.id not in mock_feed_queue.enqueued

    @pytest.mark.parametrize(
        "active,success",
        [
            (True, True),
            (False, False),
        ],
    )
    def test_active(self, db, mock_feed_queue, active, success):

        podcast = PodcastFactory(active=active, pub_date=None)

        scheduler.schedule_secondary_feeds()

        Podcast.objects.filter(queued__isnull=False).exists() is success

        if success:
            assert podcast.id in mock_feed_queue.enqueued
        else:
            assert podcast.id not in mock_feed_queue.enqueued

    @pytest.mark.parametrize(
        "promoted,followed,success",
        [
            (True, True, False),
            (True, False, False),
            (False, True, False),
            (False, False, True),
        ],
    )
    def test_promoted_or_followed(
        self,
        db,
        mock_feed_queue,
        promoted,
        followed,
        success,
    ):

        podcast = PodcastFactory(promoted=promoted, pub_date=None)

        if followed:
            FollowFactory(podcast=podcast)

        scheduler.schedule_secondary_feeds()

        Podcast.objects.filter(queued__isnull=False).exists() is success

        if success:
            assert podcast.id in mock_feed_queue.enqueued
        else:
            assert podcast.id not in mock_feed_queue.enqueued

    @pytest.mark.parametrize(
        "queued,success",
        [
            (False, True),
            (True, False),
        ],
    )
    def test_queued(self, db, mock_feed_queue, queued, success):
        podcast = PodcastFactory(
            queued=timezone.now() if queued else None, pub_date=None
        )

        scheduler.schedule_secondary_feeds()

        if success:
            assert podcast.id in mock_feed_queue.enqueued
        else:
            assert podcast.id not in mock_feed_queue.enqueued
