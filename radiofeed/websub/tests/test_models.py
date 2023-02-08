from __future__ import annotations

import pytest

from radiofeed.websub.factories import create_subscription
from radiofeed.websub.models import Subscription


class TestSubscriptionModel:
    @pytest.fixture
    def subscription(self, db):
        return create_subscription()

    def test_str(self, subscription):
        assert str(subscription) == subscription.topic

    def test_get_callback_url(self, subscription):
        assert (
            subscription.get_callback_url()
            == f"http://example.com/websub/{subscription.id}/"
        )

    def test_set_status_for_mode(self, subscription):
        subscription.set_status_for_mode("subscribe")
        assert subscription.status == Subscription.Status.SUBSCRIBED
        assert subscription.status_changed
