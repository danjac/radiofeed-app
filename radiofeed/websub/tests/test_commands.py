from __future__ import annotations

from datetime import timedelta

from django.core.management import call_command
from django.utils import timezone

from radiofeed.websub.factories import create_subscription
from radiofeed.websub.models import Subscription


class TestParseFeeds:
    def test_not_requested(self, db, mocker):
        create_subscription()
        patched = mocker.patch(
            "radiofeed.websub.subscriber.subscribe",
        )
        call_command("subscribe_websub_feeds", limit=200)
        patched.assert_called()

    def test_expired(self, db, mocker):
        now = timezone.now()
        create_subscription(
            requested=now,
            status=Subscription.Status.SUBSCRIBED,
            expires=now - timedelta(days=1),
        )
        patched = mocker.patch(
            "radiofeed.websub.subscriber.subscribe",
        )
        call_command("subscribe_websub_feeds", limit=200)
        patched.assert_called()

    def test_not_expired(self, db, mocker):
        now = timezone.now()
        create_subscription(
            requested=now,
            status=Subscription.Status.SUBSCRIBED,
            expires=now + timedelta(days=1),
        )
        patched = mocker.patch(
            "radiofeed.websub.subscriber.subscribe",
        )
        call_command("subscribe_websub_feeds", limit=200)
        patched.assert_not_called()
