from __future__ import annotations

from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.feedparser import scheduler
from radiofeed.feedparser.models import Feed, Item
from radiofeed.podcasts.factories import PodcastFactory
from radiofeed.podcasts.models import Podcast


class TestGetScheduledPodcastsForUpdate:
    @pytest.mark.parametrize(
        "active,parsed,exists",
        [
            (True, None, True),
            (False, None, False),
            (True, timedelta(days=3), True),
            (False, timedelta(days=3), False),
            (True, timedelta(hours=3), False),
        ],
    )
    def test_get_scheduled(self, db, active, parsed, exists):
        PodcastFactory(
            active=active,
            parsed=timezone.now() - parsed if parsed else None,
            update_interval=timedelta(hours=24),
        )

        assert scheduler.get_scheduled_podcasts_for_update().exists() == exists


class TestIncrementUpdateInterval:
    def test_increment(self):
        assert (
            scheduler.increment_update_interval(
                Podcast(update_interval=timedelta(days=10))
            ).days
            == 11
        )

    def test_max_value(self):
        assert (
            scheduler.increment_update_interval(
                Podcast(update_interval=timedelta(days=30))
            ).days
            == 30
        )


class TestCalcUpdateInterval:
    def test_single_date(self):
        feed = Feed(
            title="test",
            complete="yes",
            items=[
                Item(
                    guid="test",
                    title="test",
                    media_url="https://example.com",
                    media_type="audio/mpeg",
                    pub_date=timezone.now() - timedelta(days=3),
                )
            ],
        )

        assert scheduler.calc_update_interval(feed).days == 3

    def test_calc_interval(self):
        now = timezone.now()
        feed = Feed(
            title="test",
            complete="yes",
            items=[
                Item(
                    guid="test",
                    title="test",
                    media_url="https://example.com",
                    media_type="audio/mpeg",
                    pub_date=pub_date,
                )
                for pub_date in [now - timedelta(days=3 * i) for i in range(1, 12)]
            ],
        )

        assert scheduler.calc_update_interval(feed).days == 3

    def test_min_interval(self):
        now = timezone.now()
        feed = Feed(
            title="test",
            complete="yes",
            items=[
                Item(
                    guid="test",
                    title="test",
                    media_url="https://example.com",
                    media_type="audio/mpeg",
                    pub_date=pub_date,
                )
                for pub_date in [
                    now - timedelta(seconds=1200 * i) for i in range(1, 12)
                ]
            ],
        )

        assert (
            scheduler.calc_update_interval(feed).total_seconds() / 3600
        ) == pytest.approx(3)

    def test_max_interval(self):
        now = timezone.now()
        feed = Feed(
            title="test",
            complete="yes",
            items=[
                Item(
                    guid="test",
                    title="test",
                    media_url="https://example.com",
                    media_type="audio/mpeg",
                    pub_date=pub_date,
                )
                for pub_date in [now - timedelta(days=33 * i) for i in range(1, 12)]
            ],
        )

        assert scheduler.calc_update_interval(feed).days == 30
