from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.podcasts import scheduler
from radiofeed.podcasts.factories import PodcastFactory


class TestScheduler:
    @pytest.mark.parametrize(
        "pub_date,parsed,active,exists",
        [
            (None, None, True, True),
            (timedelta(days=7), None, True, True),
            (timedelta(days=7), timedelta(hours=3), True, True),
            (timedelta(days=7), timedelta(minutes=30), True, False),
            (timedelta(days=15), timedelta(hours=3), True, False),
        ],
    )
    def test_schedule_recent_feeds(self, db, pub_date, parsed, active, exists):
        now = timezone.now()
        PodcastFactory(
            pub_date=now - pub_date if pub_date else None,
            parsed=now - parsed if parsed else None,
        )
        assert scheduler.schedule_recent_feeds().exists() == exists

    @pytest.mark.parametrize(
        "pub_date,parsed,active,exists",
        [
            (None, None, True, False),
            (timedelta(days=7), None, True, False),
            (timedelta(days=7), timedelta(hours=3), True, False),
            (timedelta(days=15), timedelta(hours=3), True, True),
            (timedelta(days=15), timedelta(minutes=30), True, False),
        ],
    )
    def test_schedule_sporadic_feeds(self, db, pub_date, parsed, active, exists):
        now = timezone.now()
        PodcastFactory(
            pub_date=now - pub_date if pub_date else None,
            parsed=now - parsed if parsed else None,
        )
        assert scheduler.schedule_sporadic_feeds().exists() == exists
