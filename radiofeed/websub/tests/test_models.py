import dataclasses
import hmac
import http
import uuid
from datetime import timedelta

import pytest
import requests
from django.utils import timezone
from requests.exceptions import ReadTimeout

from radiofeed.podcasts.factories import create_podcast
from radiofeed.websub.factories import create_subscription
from radiofeed.websub.models import Subscription


@dataclasses.dataclass
class MockResponse:
    status_code: int

    def raise_for_status(self):
        if self.status_code not in range(200, 400):
            raise requests.HTTPError("oops")


class TestSubscriptionManager:
    @pytest.mark.django_db
    def test_not_subscribed(self):
        create_subscription(expires=None, mode="")

        assert Subscription.objects.for_subscribe().count() == 1

    @pytest.mark.django_db
    def test_already_requested(self):
        create_subscription(
            expires=None,
            requested=timezone.now(),
            mode="",
        )

        assert Subscription.objects.for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_not_active(self):
        create_subscription(
            podcast=create_podcast(active=False),
            expires=None,
            mode="",
        )

        assert Subscription.objects.for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_expired_none(self):
        create_subscription(expires=None, mode=Subscription.Mode.SUBSCRIBE)
        assert Subscription.objects.for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_expired(self):
        create_subscription(
            mode=Subscription.Mode.SUBSCRIBE,
            expires=timezone.now() - timedelta(days=1),
        )

        assert Subscription.objects.for_subscribe().count() == 1

    @pytest.mark.django_db
    def test_expires_in_30_mins(self):
        create_subscription(
            mode=Subscription.Mode.SUBSCRIBE,
            expires=timezone.now() + timedelta(minutes=30),
        )

        assert Subscription.objects.for_subscribe().count() == 1

    @pytest.mark.django_db
    def test_expires_in_one_day(self):
        create_subscription(
            mode=Subscription.Mode.SUBSCRIBE,
            expires=timezone.now() + timedelta(days=1),
        )

        assert Subscription.objects.for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_too_many_errors(self):
        create_subscription(
            mode=Subscription.Mode.SUBSCRIBE,
            expires=timezone.now() - timedelta(days=1),
            num_retries=3,
        )

        assert Subscription.objects.for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_expired_not_subscribed(self):
        create_subscription(
            mode="unsubscribe",
            expires=timezone.now() - timedelta(days=1),
        )

        assert Subscription.objects.for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_not_expired(self):
        create_subscription(
            mode=Subscription.Mode.SUBSCRIBE,
            expires=timezone.now() + timedelta(days=1),
        )

        assert Subscription.objects.for_subscribe().count() == 0


class TestSubscriptionModel:
    body = b"testme"
    content_type = "application/xml"

    @pytest.fixture
    def secret(self):
        return uuid.uuid4()

    @pytest.fixture
    def signature(self, secret):
        return hmac.new(secret.hex.encode("utf-8"), self.body, "sha1").hexdigest()

    @pytest.fixture
    def subscription(self):
        return create_subscription()

    def test_ok(self, rf, secret, signature):
        subscription = Subscription(secret=secret)
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1={signature}",
        )

        subscription.check_signature(req)

    def test_secret_is_none(self, rf, signature):
        subscription = Subscription(secret=None)
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1={signature}",
        )

        with pytest.raises(Subscription.InvalidSignature):
            subscription.check_signature(req)

    def test_signature_mismatch(self, rf, signature):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1={signature}",
        )

        subscription = Subscription(secret=uuid.uuid4())

        with pytest.raises(Subscription.InvalidSignature):
            subscription.check_signature(req)

    def test_content_length_too_large(self, rf, secret, signature):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            CONTENT_LENGTH=2000000000,
            HTTP_X_HUB_SIGNATURE=f"sha1={signature}",
        )
        subscription = Subscription(secret=secret)

        with pytest.raises(Subscription.InvalidSignature):
            subscription.check_signature(req)

    def test_hub_signature_header_missing(self, rf, secret):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
        )

        subscription = Subscription(secret=secret)

        with pytest.raises(Subscription.InvalidSignature):
            subscription.check_signature(req)

    def test_invalid_algo(self, rf, secret, signature):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1111={signature}",
        )

        subscription = Subscription(secret=secret)

        with pytest.raises(Subscription.InvalidSignature):
            subscription.check_signature(req)

    @pytest.mark.django_db
    def test_subscribe_accepted(self, mocker, subscription):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.ACCEPTED),
        )

        subscription.subscribe()

        subscription.refresh_from_db()

        assert subscription.secret
        assert subscription.requested

    @pytest.mark.django_db
    def test_unsubscribe(self, mocker, subscription):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.ACCEPTED),
        )

        subscription.subscribe(mode=Subscription.Mode.UNSUBSCRIBE)

        subscription.refresh_from_db()

        assert subscription.secret is None
        assert subscription.requested

    @pytest.mark.django_db
    def test_subscribe_timeout(self, mocker, subscription):
        mocker.patch(
            "requests.post",
            side_effect=ReadTimeout,
        )

        with pytest.raises(requests.ReadTimeout):
            subscription.subscribe()

        subscription.refresh_from_db()

        assert subscription.secret is None
        assert subscription.requested is None
        assert subscription.num_retries == 1

    @pytest.mark.django_db
    def test_subscribe_error(self, mocker, subscription):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.NOT_FOUND),
        )

        with pytest.raises(requests.HTTPError):
            subscription.subscribe()

        subscription.refresh_from_db()

        assert subscription.secret is None
        assert subscription.requested is None
        assert subscription.num_retries == 1

    @pytest.mark.django_db
    def test_verify_subscribe(self, subscription):
        subscription.verify()

        assert subscription.mode == Subscription.Mode.SUBSCRIBE
        assert subscription.expires

    @pytest.mark.django_db
    def test_verify_unsubscribe(self, subscription):
        subscription.verify(mode=Subscription.Mode.UNSUBSCRIBE)

        assert subscription.mode == Subscription.Mode.UNSUBSCRIBE
        assert subscription.expires is None
