from __future__ import annotations

import dataclasses
import http

import pytest
import requests

from radiofeed.websub import subscriber
from radiofeed.websub.factories import create_subscription
from radiofeed.websub.models import Subscription


@dataclasses.dataclass
class MockResponse:
    status_code: int

    def raise_for_status(self):
        if self.status_code not in range(200, 400):
            raise requests.HTTPError("oops")


@pytest.fixture
def subscription(db):
    return create_subscription()


class TestSubscribe:
    def test_ok(self, mocker, subscription):
        mocker.patch(
            "requests.get", return_value=MockResponse(status_code=http.HTTPStatus.OK)
        )

        subscriber.subscribe(subscription)
        subscription.refresh_from_db()

        assert subscription.requested
        assert subscription.status == Subscription.Status.SUBSCRIBED
        assert subscription.status_changed

    def test_accepted(self, mocker, subscription):
        mocker.patch(
            "requests.get",
            return_value=MockResponse(status_code=http.HTTPStatus.ACCEPTED),
        )

        subscriber.subscribe(subscription)

        subscription.refresh_from_db()

        assert subscription.requested
        assert subscription.status == Subscription.Status.PENDING
        assert subscription.status_changed is None
