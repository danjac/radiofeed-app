from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.podcasts import feed_scheduler
from radiofeed.podcasts.factories import PodcastFactory


class TestSchedule:
    def test_schedule(self, db, mocker):

        patched = mocker.patch(
            "radiofeed.podcasts.tasks.feed_update.map",
        )

        feed_scheduler.schedule(300)

        patched.assert_called()


class TestGetScheduledFeeds:
    @pytest.mark.parametrize(
        "active,pub_date,parsed,exists",
        [
            (
                True,
                None,
                None,
                True,
            ),
            (
                True,
                timedelta(hours=3),
                timedelta(hours=1),
                True,
            ),
            (
                True,
                timedelta(hours=3),
                timedelta(minutes=30),
                False,
            ),
            (
                True,
                timedelta(days=3),
                timedelta(hours=3),
                True,
            ),
            (
                True,
                timedelta(days=3),
                timedelta(hours=1),
                False,
            ),
            (
                True,
                timedelta(days=8),
                timedelta(hours=8),
                True,
            ),
            (
                True,
                timedelta(days=8),
                timedelta(hours=9),
                True,
            ),
            (
                True,
                timedelta(days=14),
                timedelta(hours=8),
                False,
            ),
            (
                True,
                timedelta(days=15),
                timedelta(hours=8),
                False,
            ),
            (
                True,
                timedelta(days=15),
                timedelta(hours=24),
                True,
            ),
        ],
    )
    def test_get_scheduled_feeds(self, db, mocker, active, pub_date, parsed, exists):
        now = timezone.now()

        PodcastFactory(
            active=active,
            pub_date=now - pub_date if pub_date else None,
            parsed=now - parsed if parsed else None,
        )

        assert feed_scheduler.get_scheduled_feeds().exists() == exists
