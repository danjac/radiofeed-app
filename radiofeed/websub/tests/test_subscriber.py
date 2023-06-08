import dataclasses
import http
from datetime import timedelta

import pytest
import requests
from django.utils import timezone
from requests.exceptions import ReadTimeout

from radiofeed.podcasts.factories import create_podcast
from radiofeed.websub import subscriber
from radiofeed.websub.factories import create_subscription


@dataclasses.dataclass
class MockResponse:
    status_code: int

    def raise_for_status(self):
        if self.status_code not in range(200, 400):
            raise requests.HTTPError("oops")


class TestGetSubscriptionsForUpdate:
    @pytest.mark.django_db
    def test_not_subscribed(self):
        create_subscription(expires=None, mode="")

        assert subscriber.get_subscriptions_for_update().count() == 1

    @pytest.mark.django_db
    def test_already_subscribed(self):
        create_subscription(
            expires=None,
            mode=subscriber.SUBSCRIBE,
        )

        assert subscriber.get_subscriptions_for_update().count() == 0

    @pytest.mark.django_db
    def test_not_active(self):
        create_subscription(
            podcast=create_podcast(active=False),
            expires=None,
            mode="",
        )

        assert subscriber.get_subscriptions_for_update().count() == 0

    @pytest.mark.django_db
    def test_expired_none(self):
        create_subscription(expires=None, mode=subscriber.SUBSCRIBE)
        assert subscriber.get_subscriptions_for_update().count() == 0

    @pytest.mark.django_db
    def test_expired(self):
        create_subscription(
            mode=subscriber.SUBSCRIBE,
            expires=timezone.now() - timedelta(days=1),
        )

        assert subscriber.get_subscriptions_for_update().count() == 1

    @pytest.mark.django_db
    def test_expires_in_30_mins(self):
        create_subscription(
            mode=subscriber.SUBSCRIBE,
            expires=timezone.now() + timedelta(minutes=30),
        )

        assert subscriber.get_subscriptions_for_update().count() == 1

    @pytest.mark.django_db
    def test_expires_in_one_day(self):
        create_subscription(
            mode=subscriber.SUBSCRIBE,
            expires=timezone.now() + timedelta(days=1),
        )

        assert subscriber.get_subscriptions_for_update().count() == 0

    @pytest.mark.django_db
    def test_too_many_errors(self):
        create_subscription(
            mode=subscriber.SUBSCRIBE,
            expires=timezone.now() - timedelta(days=1),
            num_retries=3,
        )

        assert subscriber.get_subscriptions_for_update().count() == 0

    @pytest.mark.django_db
    def test_expired_not_subscribed(self):
        create_subscription(
            mode=subscriber.UNSUBSCRIBE,
            expires=timezone.now() - timedelta(days=1),
        )

        assert subscriber.get_subscriptions_for_update().count() == 0

    @pytest.mark.django_db
    def test_not_expired(self):
        create_subscription(
            mode=subscriber.SUBSCRIBE,
            expires=timezone.now() + timedelta(days=1),
        )

        assert subscriber.get_subscriptions_for_update().count() == 0


class TestSubscribe:
    @pytest.fixture
    def subscription(self):
        return create_subscription()

    @pytest.mark.django_db
    def test_subscribe_accepted(self, mocker, subscription):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.ACCEPTED),
        )

        subscriber.subscribe(subscription)

        subscription.refresh_from_db()

        assert subscription.mode == subscriber.SUBSCRIBE
        assert subscription.secret

    @pytest.mark.django_db
    def test_unsubscribe(self, mocker, subscription):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.ACCEPTED),
        )

        subscriber.subscribe(subscription, mode=subscriber.UNSUBSCRIBE)

        subscription.refresh_from_db()

        assert subscription.mode == subscriber.UNSUBSCRIBE
        assert subscription.secret is None

    @pytest.mark.django_db
    def test_subscribe_timeout(self, mocker, subscription):
        mocker.patch(
            "requests.post",
            side_effect=ReadTimeout,
        )

        with pytest.raises(requests.ReadTimeout):
            subscriber.subscribe(subscription)

        subscription.refresh_from_db()

        assert subscription.secret is None
        assert subscription.num_retries == 1

    @pytest.mark.django_db
    def test_subscribe_error(self, mocker, subscription):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.NOT_FOUND),
        )

        with pytest.raises(requests.HTTPError):
            subscriber.subscribe(subscription)

        subscription.refresh_from_db()

        assert subscription.secret is None
        assert subscription.num_retries == 1
