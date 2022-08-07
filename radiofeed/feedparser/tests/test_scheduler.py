from __future__ import annotations

from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.feedparser import scheduler
from radiofeed.feedparser.factories import FeedFactory, ItemFactory
from radiofeed.feedparser.models import Feed, Item
from radiofeed.podcasts.factories import PodcastFactory
from radiofeed.podcasts.models import Podcast


class TestGetNextScheduledUpdate:
    @pytest.mark.parametrize(
        "parsed,pub_date,frequency,diff",
        [
            (None, None, timedelta(hours=24), 1),
            (timedelta(days=3), None, timedelta(hours=24), 1),
            (None, timedelta(days=3), timedelta(hours=24), 1),
            (timedelta(days=3), timedelta(days=4), timedelta(days=1), 1),
            (timedelta(days=3), timedelta(days=4), timedelta(days=7), 24 * 3),
            (timedelta(days=4), timedelta(days=3), timedelta(days=7), 24 * 3),
            (timedelta(days=4), timedelta(days=60), timedelta(days=7), 24 * 3),
            (timedelta(days=4), timedelta(days=3), timedelta(days=30), 24 * 26),
        ],
    )
    def test_get_scheduled(self, parsed, pub_date, frequency, diff):
        now = timezone.now()
        podcast = Podcast(
            parsed=now - parsed if parsed else None,
            pub_date=now - pub_date if pub_date else None,
            frequency=frequency,
        )

        assert (
            scheduler.get_next_scheduled_update(podcast) - now
        ).total_seconds() / 3600 <= diff, (parsed, pub_date, frequency, diff)


class TestScheduledPodcastsForUpdate:
    @pytest.mark.parametrize(
        "active,parsed,pub_date,frequency,exists",
        [
            (True, None, None, timedelta(hours=24), True),
            (False, None, None, timedelta(hours=24), False),
            (True, timedelta(days=3), timedelta(days=3), timedelta(hours=24), True),
            (False, timedelta(days=3), timedelta(days=3), timedelta(hours=24), False),
            (True, timedelta(hours=3), timedelta(hours=3), timedelta(hours=24), False),
            (True, timedelta(days=15), timedelta(days=15), timedelta(days=30), False),
            (True, timedelta(days=30), timedelta(days=90), timedelta(days=30), True),
        ],
    )
    def test_get_scheduled(self, db, active, parsed, pub_date, frequency, exists):
        PodcastFactory(
            active=active,
            parsed=timezone.now() - parsed if parsed else None,
            pub_date=timezone.now() - pub_date if pub_date else None,
            frequency=frequency,
        )

        assert scheduler.scheduled_podcasts_for_update().exists() == exists, (
            active,
            parsed,
            pub_date,
            frequency,
            exists,
        )


class TestReschedule:
    def test_pub_date_none(self):
        assert scheduler.reschedule(None, timedelta(hours=24)).days == 1

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

    def test_median_empty(self):

        pub_date = timezone.now() - timedelta(days=3)

        items = [Item(**ItemFactory(pub_date=pub_date)) for _ in range(12)]

        feed = Feed(**FeedFactory(), items=items)

        assert scheduler.schedule(feed).days == 3

    def test_no_outliers(self):

        items = []
        last = timezone.now()

        for day in [7] * 12:

            pub_date = last - timedelta(days=day)
            items.append(Item(**ItemFactory(pub_date=pub_date)))
            last = pub_date

        feed = Feed(**FeedFactory(), items=items)

        assert scheduler.schedule(feed).days == pytest.approx(7)

    def test_variation(self):

        items = []
        last = timezone.now()

        for day in [4, 3, 4, 2, 5, 2, 4, 4, 3, 4, 4, 4, 6, 5, 7, 7, 7, 7, 3]:

            pub_date = last - timedelta(days=day)
            items.append(Item(**ItemFactory(pub_date=pub_date)))
            last = pub_date

        feed = Feed(**FeedFactory(), items=items)

        assert scheduler.schedule(feed).days == pytest.approx(4)

    def test_min_frequency(self):
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

    def test_max_frequency(self):
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
