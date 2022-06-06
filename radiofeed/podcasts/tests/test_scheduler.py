from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.podcasts import scheduler
from radiofeed.podcasts.factories import PodcastFactory


class TestSchedulePodcastsForUpdate:
    @pytest.mark.parametrize(
        "pub_date,parsed,exists",
        [
            (
                timedelta(hours=3),
                timedelta(hours=2),
                True,
            ),
            (
                timedelta(hours=24),
                timedelta(hours=2),
                False,
            ),
            (
                timedelta(hours=3),
                timedelta(minutes=30),
                False,
            ),
            (
                timedelta(hours=24),
                timedelta(hours=1),
                False,
            ),
            (
                timedelta(hours=24),
                timedelta(hours=4),
                True,
            ),
            (
                timedelta(days=3),
                timedelta(hours=4),
                True,
            ),
            (
                timedelta(days=7),
                timedelta(hours=4),
                False,
            ),
            (
                timedelta(days=7),
                timedelta(hours=24),
                True,
            ),
            (
                timedelta(days=8),
                timedelta(hours=23),
                False,
            ),
            (
                timedelta(days=8),
                timedelta(hours=24),
                True,
            ),
            (
                timedelta(days=14),
                timedelta(hours=24),
                False,
            ),
            (
                timedelta(days=14),
                timedelta(hours=25),
                False,
            ),
            (
                timedelta(days=14),
                timedelta(days=7),
                True,
            ),
        ],
    )
    def test_schedule(self, db, pub_date, parsed, exists):
        now = timezone.now()
        PodcastFactory(pub_date=now - pub_date, parsed=now - parsed)
        assert scheduler.schedule_podcasts_for_update().exists() == exists

    def test_parsed_is_null(self, db):
        PodcastFactory(parsed=None)
        assert scheduler.schedule_podcasts_for_update().exists()

    def test_pub_date_is_null(self, db):
        PodcastFactory(parsed=timezone.now() - timedelta(hours=2), pub_date=None)
        assert scheduler.schedule_podcasts_for_update().exists()

    def test_inactive(self, db):
        PodcastFactory(parsed=None, active=False)
        assert not scheduler.schedule_podcasts_for_update().exists()
