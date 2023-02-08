from __future__ import annotations

from datetime import timedelta

import pytest

from django.core.management import call_command
from django.utils import timezone

from radiofeed.websub.factories import create_subscription


class TestParseFeeds:
    @pytest.fixture
    def subscribe(self, mocker):
        return mocker.patch(
            "radiofeed.websub.subscriber.subscribe",
        )

    def test_not_requested(self, db, subscribe):
        create_subscription()
        call_command("subscribe_websub_feeds", limit=200)
        subscribe.assert_called()

    def test_expired_none(self, db, subscribe):
        now = timezone.now()
        create_subscription(
            requested=now,
            expires=None,
        )
        call_command("subscribe_websub_feeds", limit=200)
        subscribe.assert_not_called()

    def test_expired(self, db, subscribe):
        now = timezone.now()
        create_subscription(
            requested=now,
            expires=now - timedelta(days=1),
        )
        call_command("subscribe_websub_feeds", limit=200)
        subscribe.assert_called()

    def test_not_expired(self, db, subscribe):
        now = timezone.now()
        create_subscription(
            requested=now,
            expires=now + timedelta(days=1),
        )
        call_command("subscribe_websub_feeds", limit=200)
        subscribe.assert_not_called()
