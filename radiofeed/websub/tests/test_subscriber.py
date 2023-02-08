from __future__ import annotations

import dataclasses
import hmac
import http
import uuid

import pytest
import requests

from radiofeed.websub import subscriber
from radiofeed.websub.factories import create_subscription


@dataclasses.dataclass
class MockResponse:
    status_code: int

    def raise_for_status(self):
        if self.status_code not in range(200, 400):
            raise requests.HTTPError("oops")


@pytest.fixture
def subscription(db):
    return create_subscription()


class TestCheckSignature:
    body = b"testme"
    content_type = "application/xml"

    def test_ok(self, rf, subscription):
        sig = hmac.new(
            subscription.secret.hex.encode("utf-8"), self.body, "sha1"
        ).hexdigest()

        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
        )

        assert subscriber.check_signature(req, subscription)

    def test_signature_mismatch(self, rf, subscription):
        sig = hmac.new(uuid.uuid4().hex.encode("utf-8"), self.body, "sha1").hexdigest()

        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
        )

        assert not subscriber.check_signature(req, subscription)

    def test_content_length_too_large(self, rf, subscription):
        sig = hmac.new(
            subscription.secret.hex.encode("utf-8"), self.body, "sha1"
        ).hexdigest()

        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            CONTENT_LENGTH=2000000000,
            HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
        )

        assert not subscriber.check_signature(req, subscription)

    def test_hub_signature_header_missing(self, rf, subscription):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
        )

        assert not subscriber.check_signature(req, subscription)

    def test_invalid_algo(self, rf, subscription):
        sig = hmac.new(
            subscription.secret.hex.encode("utf-8"), self.body, "sha1"
        ).hexdigest()

        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1111={sig}",
        )

        assert not subscriber.check_signature(req, subscription)


class TestSubscribe:
    def test_ok(self, mocker, subscription):
        mocker.patch(
            "requests.get", return_value=MockResponse(status_code=http.HTTPStatus.OK)
        )

        subscriber.subscribe(subscription)
        subscription.refresh_from_db()

        assert subscription.requested
        assert subscription.mode == "subscribe"
        assert subscription.verified

    def test_accepted(self, mocker, subscription):
        mocker.patch(
            "requests.get",
            return_value=MockResponse(status_code=http.HTTPStatus.ACCEPTED),
        )

        subscriber.subscribe(subscription)

        subscription.refresh_from_db()

        assert subscription.requested
        assert not subscription.mode
        assert subscription.verified is None

    def test_error(self, mocker, subscription):
        mocker.patch(
            "requests.get",
            return_value=MockResponse(status_code=http.HTTPStatus.NOT_FOUND),
        )

        with pytest.raises(requests.HTTPError):
            subscriber.subscribe(subscription)

        subscription.refresh_from_db()

        assert subscription.requested is None
        assert not subscription.mode
        assert subscription.verified is None
