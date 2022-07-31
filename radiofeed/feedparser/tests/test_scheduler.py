from __future__ import annotations

from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.feedparser import scheduler
from radiofeed.feedparser.factories import FeedFactory, ItemFactory
from radiofeed.feedparser.models import Feed, Item
from radiofeed.podcasts.factories import PodcastFactory


class TestScheduledPodcastsForUpdate:
    @pytest.mark.parametrize(
        "active,parsed,pub_date,update_interval,exists",
        [
            (True, None, None, timedelta(hours=24), True),
            (False, None, None, timedelta(hours=24), False),
            (True, timedelta(days=3), timedelta(days=3), timedelta(hours=24), True),
            (True, timedelta(hours=2), timedelta(hours=3), timedelta(hours=3), False),
            (False, timedelta(days=3), timedelta(days=3), timedelta(hours=24), False),
            (True, timedelta(hours=3), timedelta(hours=3), timedelta(hours=24), False),
            (True, timedelta(days=15), timedelta(days=15), timedelta(days=30), False),
            (True, timedelta(days=30), timedelta(days=90), timedelta(days=30), True),
        ],
    )
    def test_get_scheduled(self, db, active, parsed, pub_date, update_interval, exists):
        PodcastFactory(
            active=active,
            parsed=timezone.now() - parsed if parsed else None,
            pub_date=timezone.now() - pub_date if pub_date else None,
            update_interval=update_interval,
        )

        assert scheduler.scheduled_podcasts_for_update().exists() == exists, (
            active,
            parsed,
            pub_date,
            update_interval,
            exists,
        )


class TestReschedule:
    def test_reschedule_no_change(self):
        assert scheduler.reschedule(timezone.now(), timedelta(days=10)).days == 10

    def test_increment(self):
        assert scheduler.reschedule(
            timezone.now() - timedelta(days=1), timedelta(hours=24)
        ).total_seconds() / 3600 == pytest.approx(26.4)

    def test_max_value(self):
        assert (
            scheduler.reschedule(
                timezone.now() - timedelta(days=33), timedelta(days=30)
            ).days
            == 30
        )


class TestSchedule:
    def test_single_date(self):
        feed = Feed(
            **FeedFactory(),
            items=[
                Item(
                    **ItemFactory(
                        pub_date=timezone.now() - timedelta(days=3),
                    )
                )
            ],
        )

        assert scheduler.schedule(feed).days == 3

    def test_single_date_gt_max(self):
        feed = Feed(
            **FeedFactory(),
            items=[
                Item(
                    **ItemFactory(
                        pub_date=timezone.now() - timedelta(days=33),
                    )
                )
            ],
        )

        assert scheduler.schedule(feed).days == 30

    def test_varied(self):

        items = []
        last = timezone.now()

        for day in [4, 3, 4, 2, 5, 2, 4, 4, 3, 4, 4, 4, 6, 5, 7, 7, 7, 7, 3]:

            pub_date = last - timedelta(days=day)
            items.append(Item(**ItemFactory(pub_date=pub_date)))
            last = pub_date

        feed = Feed(**FeedFactory(), items=items)

        assert scheduler.schedule(feed).days == pytest.approx(4)

    def test_min_interval(self):
        now = timezone.now()
        feed = Feed(
            **FeedFactory(),
            items=[
                Item(
                    **ItemFactory(
                        pub_date=pub_date,
                    )
                )
                for pub_date in [
                    now - timedelta(seconds=1200 * i) for i in range(1, 12)
                ]
            ],
        )

        assert (scheduler.schedule(feed).total_seconds() / 3600) == pytest.approx(3)

    def test_max_interval(self):
        now = timezone.now()
        feed = Feed(
            **FeedFactory(),
            items=[
                Item(
                    **ItemFactory(
                        pub_date=pub_date,
                    )
                )
                for pub_date in [now - timedelta(days=33 * i) for i in range(1, 12)]
            ],
        )

        assert scheduler.schedule(feed).days == 30
