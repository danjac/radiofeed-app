from __future__ import annotations

import pytest

from radiofeed.websub.factories import create_subscription


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
