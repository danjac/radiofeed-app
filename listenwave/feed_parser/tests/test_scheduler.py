import pytest
from django.utils import timezone

from listenwave.feed_parser import scheduler
from listenwave.feed_parser.models import Feed, Item
from listenwave.feed_parser.tests.factories import FeedFactory, ItemFactory


class TestReschedule:
    def test_pub_date_none(self):
        self.assert_hours_diff(
            scheduler.reschedule(None, timezone.timedelta(hours=24)), 24
        )

    def test_frequency_none(self):
        self.assert_hours_diff(scheduler.reschedule(timezone.now(), None), 24)

    def test_reschedule_no_change(self):
        assert (
            scheduler.reschedule(timezone.now(), timezone.timedelta(days=10)).days == 10
        )

    def test_increment(self):
        self.assert_hours_diff(
            scheduler.reschedule(
                timezone.now() - timezone.timedelta(days=1),
                timezone.timedelta(hours=24),
            ),
            24.24,
        )

    def assert_hours_diff(self, delta, hours):
        assert delta.total_seconds() / 3600 == pytest.approx(hours)


class TestSchedule:
    def test_single_date(self):
        feed = Feed(
            **FeedFactory(
                items=[
                    Item(
                        **ItemFactory(
                            pub_date=timezone.now() - timezone.timedelta(days=3),
                        )
                    )
                ],
            )
        )

        assert scheduler.schedule(feed).days == 3

    def test_single_date_rescheduled(self):
        feed = Feed(
            **FeedFactory(
                items=[
                    Item(
                        **ItemFactory(
                            pub_date=timezone.now() - timezone.timedelta(days=33),
                        )
                    )
                ],
            )
        )

        assert scheduler.schedule(feed).days == 33

    def test_median_empty(self):
        pub_date = timezone.now() - timezone.timedelta(days=3)

        items = [Item(**ItemFactory(pub_date=pub_date)) for _ in range(12)]

        feed = Feed(**FeedFactory(items=items))

        assert scheduler.schedule(feed).days == 3

    def test_no_outliers(self):
        items = []
        last = timezone.now()

        for day in [7] * 12:
            pub_date = last - timezone.timedelta(days=day)
            items.append(Item(**ItemFactory(pub_date=pub_date)))
            last = pub_date

        feed = Feed(**FeedFactory(items=items))

        assert scheduler.schedule(feed).days == pytest.approx(7)

    def test_variation(self):
        items = []
        last = timezone.now()

        for day in [4, 3, 4, 2, 5, 2, 4, 4, 3, 4, 4, 4, 6, 5, 7, 7, 7, 7, 3]:
            pub_date = last - timezone.timedelta(days=day)
            items.append(Item(**ItemFactory(pub_date=pub_date)))
            last = pub_date

        feed = Feed(**FeedFactory(items=items))

        assert scheduler.schedule(feed).days == pytest.approx(4)

    def test_regular_pattern(self):
        items = []
        last = timezone.now()

        for day in [3, 4] * 12:
            pub_date = last - timezone.timedelta(days=day)
            items.append(Item(**ItemFactory(pub_date=pub_date)))
            last = pub_date

        feed = Feed(**FeedFactory(items=items))

        assert scheduler.schedule(feed).days == pytest.approx(3)

    def test_min_frequency(self):
        now = timezone.now()
        feed = Feed(
            **FeedFactory(
                items=[
                    Item(
                        **ItemFactory(
                            pub_date=pub_date,
                        )
                    )
                    for pub_date in [
                        now - timezone.timedelta(seconds=1200 * i) for i in range(1, 12)
                    ]
                ],
            )
        )

        assert (scheduler.schedule(feed).total_seconds() / 3600) == pytest.approx(1)

    def test_rescheduled(self):
        now = timezone.now()
        feed = Feed(
            **FeedFactory(
                items=[
                    Item(
                        **ItemFactory(
                            pub_date=pub_date,
                        )
                    )
                    for pub_date in [
                        now - timezone.timedelta(days=33 * i) for i in range(1, 12)
                    ]
                ],
            )
        )

        assert scheduler.schedule(feed).days == 33
