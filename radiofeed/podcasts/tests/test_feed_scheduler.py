from datetime import timedelta
from unittest import mock

import pytest

from django.utils import timezone

from radiofeed.podcasts import feed_scheduler, feed_updater
from radiofeed.podcasts.factories import PodcastFactory


class TestRemoveFeedsFromQueue:
    def test_remove(self, db):
        first = PodcastFactory(queued=timezone.now() - timedelta(hours=2))
        second = PodcastFactory(queued=timezone.now() - timedelta(minutes=30))

        feed_scheduler.remove_feeds_from_queue(timedelta(hours=1))

        first.refresh_from_db()
        assert first.queued is None

        second.refresh_from_db()
        assert second.queued is not None


class TestSchedule:
    def test_schedule(self, db, mocker):
        podcast = PodcastFactory(parsed=None, pub_date=None)

        patched = mocker.patch("radiofeed.podcasts.feed_scheduler.enqueue")

        assert feed_scheduler.schedule(100) == {podcast.id}

        patched.assert_called_with(podcast.id)


class TestEnqueue:
    def test_enqueue(self, mocker, podcast):

        mock_queue = mock.Mock()
        mocker.patch(
            "radiofeed.podcasts.feed_scheduler.get_queue",
            return_value=mock_queue,
        )
        feed_scheduler.enqueue(podcast.id)

        mock_queue.enqueue.assert_called_with(
            feed_updater.update,
            args=(podcast.id,),
        )
        podcast.refresh_from_db()
        assert podcast.queued


class TestGetScheduledFeeds:
    @pytest.mark.parametrize(
        "active,queued,pub_date,parsed,exists",
        [
            (
                True,
                False,
                None,
                None,
                True,
            ),
            (
                False,
                False,
                None,
                None,
                False,
            ),
            (
                True,
                False,
                timedelta(hours=3),
                timedelta(hours=1),
                True,
            ),
            (
                True,
                True,
                timedelta(hours=3),
                timedelta(hours=1),
                False,
            ),
            (
                True,
                False,
                timedelta(hours=3),
                timedelta(minutes=30),
                False,
            ),
            (
                True,
                False,
                timedelta(days=3),
                timedelta(hours=3),
                True,
            ),
            (
                True,
                False,
                timedelta(days=3),
                timedelta(hours=1),
                False,
            ),
            (
                True,
                False,
                timedelta(days=8),
                timedelta(hours=8),
                True,
            ),
            (
                True,
                False,
                timedelta(days=8),
                timedelta(hours=9),
                True,
            ),
            (
                True,
                False,
                timedelta(days=14),
                timedelta(hours=8),
                False,
            ),
            (
                True,
                False,
                timedelta(days=15),
                timedelta(hours=8),
                False,
            ),
            (
                True,
                False,
                timedelta(days=15),
                timedelta(hours=24),
                True,
            ),
        ],
    )
    def test_get_scheduled_feeds(
        self, db, mocker, active, queued, pub_date, parsed, exists
    ):
        now = timezone.now()

        PodcastFactory(
            active=active,
            queued=now if queued else None,
            pub_date=now - pub_date if pub_date else None,
            parsed=now - parsed if parsed else None,
        )

        assert feed_scheduler.get_scheduled_feeds().exists() == exists
