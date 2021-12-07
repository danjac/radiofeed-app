import hmac
import http
import uuid

from datetime import timedelta

import pytest
import requests

from django.utils import timezone

from jcasts.websub import subscriber
from jcasts.websub.factories import SubscriptionFactory
from jcasts.websub.models import Subscription


class MockResponse:
    def __init__(self, status_code=None):
        self.status_code = status_code
        self.content = b"ok"

    def raise_for_status(self):
        pass


class MockBadResponse(MockResponse):
    def raise_for_status(self):
        if self.status_code:
            raise requests.HTTPError(response=self)
        raise requests.RequestException()


class TestSubscribe:
    def test_accepted(self, subscription, mocker):
        mock_post = mocker.patch(
            "requests.post", return_value=MockResponse(http.HTTPStatus.ACCEPTED)
        )
        assert subscriber.subscribe(subscription.id)

        mock_post.assert_called()

        subscription.refresh_from_db()

        assert subscription.status is None
        assert subscription.status_changed is None

        assert subscription.requests == 1
        assert subscription.requested

    def test_subscribe(self, subscription, mocker):
        mock_post = mocker.patch(
            "requests.post", return_value=MockResponse(http.HTTPStatus.OK)
        )
        assert subscriber.subscribe(subscription.id)

        mock_post.assert_called()

        subscription.refresh_from_db()

        assert subscription.status == Subscription.Status.SUBSCRIBED
        assert subscription.status_changed

        assert subscription.requests == 1
        assert subscription.requested

    def test_denied(self, subscription, mocker):
        mock_post = mocker.patch(
            "requests.post", return_value=MockResponse(http.HTTPStatus.OK)
        )
        assert subscriber.subscribe(subscription.id, mode="denied")

        mock_post.assert_called()

        subscription.refresh_from_db()

        assert subscription.status == Subscription.Status.DENIED
        assert subscription.status_changed

        assert subscription.requests == 1
        assert subscription.requested

    def test_http_error(self, subscription, mocker):
        mock_post = mocker.patch(
            "requests.post",
            return_value=MockBadResponse(http.HTTPStatus.INTERNAL_SERVER_ERROR),
        )
        result = subscriber.subscribe(subscription.id)
        assert not result
        assert result.status == http.HTTPStatus.INTERNAL_SERVER_ERROR

        mock_post.assert_called()

        subscription.refresh_from_db()

        assert subscription.exception
        assert subscription.status is None
        assert subscription.status_changed is None

        assert subscription.requests == 1
        assert subscription.requested

    def test_network_error(self, subscription, mocker):
        mock_post = mocker.patch(
            "requests.post",
            return_value=MockBadResponse(),
        )
        result = subscriber.subscribe(subscription.id)
        assert not result
        assert result.status is None

        mock_post.assert_called()

        subscription.refresh_from_db()

        assert subscription.exception
        assert subscription.status is None
        assert subscription.status_changed is None

        assert subscription.requests == 1
        assert subscription.requested

    def test_not_found(self, db):
        assert not subscriber.subscribe(uuid.uuid4())


class TestEnqueue:
    @pytest.mark.parametrize(
        "status,requests,subscribes",
        [
            (None, 0, True),
            (None, 2, True),
            (None, 3, False),
            (None, 5, False),
            (Subscription.Status.SUBSCRIBED, 0, False),
        ],
    )
    def test_enqueue_status_none(
        self, db, mock_subscribe, status, requests, subscribes
    ):

        SubscriptionFactory(status=status, requests=requests)

        subscriber.enqueue()

        if subscribes:
            mock_subscribe.assert_called()
        else:
            mock_subscribe.assert_not_called()

    @pytest.mark.parametrize(
        "status,expires,subscribes",
        [
            (Subscription.Status.DENIED, False, False),
            (Subscription.Status.SUBSCRIBED, False, False),
            (Subscription.Status.SUBSCRIBED, timedelta(days=3), False),
            (Subscription.Status.SUBSCRIBED, timedelta(days=-3), True),
        ],
    )
    def test_enqueue_expired(self, db, mock_subscribe, status, expires, subscribes):
        now = timezone.now()

        SubscriptionFactory(
            status=status,
            expires=now + expires if expires else None,
        )
        subscriber.enqueue()

        if subscribes:
            mock_subscribe.assert_called()
        else:
            mock_subscribe.assert_not_called()


class TestCheckSignature:
    def test_ok(self, rf, subscription):

        body = b"testme"

        sig = hmac.new(
            subscription.secret.hex.encode("utf-8"), body, "sha1"
        ).hexdigest()

        req = rf.post(
            "/",
            body,
            content_type="application/xml",
            HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
        )

        assert subscriber.check_signature(req, subscription) is True

    def test_signature_mismatch(self, rf, subscription):

        body = b"testme"

        sig = hmac.new(uuid.uuid4().hex.encode("utf-8"), body, "sha1").hexdigest()

        req = rf.post(
            "/",
            body,
            content_type="application/xml",
            HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
        )

        assert subscriber.check_signature(req, subscription) is False

    def test_invalid_algo(self, rf, subscription):

        body = b"testme"

        sig = hmac.new(
            subscription.secret.hex.encode("utf-8"), body, "sha1"
        ).hexdigest()

        req = rf.post(
            "/",
            body,
            content_type="application/xml",
            HTTP_X_HUB_SIGNATURE=f"sha1111={sig}",
        )

        assert subscriber.check_signature(req, subscription) is False

    def test_hub_signature_header_missing(self, rf, subscription):

        req = rf.post(
            "/",
            b"testme",
            content_type="application/xml",
        )

        assert subscriber.check_signature(req, subscription) is False

    def test_content_length_too_large(self, rf, subscription):

        body = b"testme"

        sig = hmac.new(
            subscription.secret.hex.encode("utf-8"), body, "sha1"
        ).hexdigest()

        req = rf.post(
            "/",
            body,
            content_type="application/xml",
            CONTENT_LENGTH=2000000000,
            HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
        )

        assert subscriber.check_signature(req, subscription) is False
