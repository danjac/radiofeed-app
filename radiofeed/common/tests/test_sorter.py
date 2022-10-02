from __future__ import annotations

from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.common.sorter import Sorter
from radiofeed.podcasts.factories import PodcastFactory
from radiofeed.podcasts.models import Podcast


class TestSorter:
    @pytest.fixture
    def podcasts(self, db):
        return [
            PodcastFactory(pub_date=timezone.now()),
            PodcastFactory(pub_date=timezone.now() - timedelta(days=3)),
        ]

    def test_default_value(self, rf):
        req = rf.get("/")
        sorter = Sorter(req)
        assert sorter.value == "desc"
        assert sorter.is_desc

    def test_asc_value(self, rf):
        req = rf.get("/", {"o": "asc"})
        sorter = Sorter(req)
        assert sorter.value == "asc"
        assert sorter.is_asc

    def test_desc_value(self, rf):
        req = rf.get("/", {"o": "desc"})
        sorter = Sorter(req)
        assert sorter.value == "desc"
        assert sorter.is_desc

    def test_str(self, rf):
        req = rf.get("/")
        sorter = Sorter(req)
        assert str(sorter) == "desc"

    def test_qs_if_asc(self, rf):
        req = rf.get("/", {"o": "asc"})
        sorter = Sorter(req)
        assert sorter.qs == "o=desc"

    def test_qs_if_desc(self, rf):
        req = rf.get("/", {"o": "desc"})
        sorter = Sorter(req)
        assert sorter.qs == "o=asc"

    def test_order_by_asc(self, rf, db, podcasts):
        req = rf.get("/", {"o": "asc"})

        sorter = Sorter(req)
        assert list(sorter.order_by(Podcast.objects.all(), "pub_date")) == [
            podcasts[1],
            podcasts[0],
        ]

    def test_order_by_desc(self, rf, db, podcasts):
        req = rf.get("/", {"o": "desc"})

        sorter = Sorter(req)
        assert list(sorter.order_by(Podcast.objects.all(), "pub_date")) == [
            podcasts[0],
            podcasts[1],
        ]
