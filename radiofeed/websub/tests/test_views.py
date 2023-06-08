import uuid

import pytest

from radiofeed.asserts import assert_no_content, assert_not_found, assert_ok
from radiofeed.websub import signature, subscriber
from radiofeed.websub.factories import create_subscription


class TestCallback:
    @pytest.fixture
    def subscription(self):
        return create_subscription(mode=subscriber.SUBSCRIBE, secret=uuid.uuid4())

    @pytest.mark.django_db
    def test_post(self, client, mocker, subscription):
        mocker.patch("radiofeed.websub.signature.check_signature")

        assert_no_content(client.post(subscription.get_callback_url()))
        subscription.refresh_from_db()
        assert subscription.podcast.priority

    @pytest.mark.django_db
    def test_post_invalid_signature(self, client, mocker, subscription):
        mocker.patch(
            "radiofeed.websub.signature.check_signature",
            side_effect=signature.InvalidSignature,
        )

        assert_no_content(client.post(subscription.get_callback_url()))

        subscription.refresh_from_db()
        assert not subscription.podcast.priority

    @pytest.mark.django_db
    def test_get(self, client, subscription):
        assert_ok(
            client.get(
                subscription.get_callback_url(),
                {
                    "hub.mode": "subscribe",
                    "hub.challenge": "OK",
                    "hub.topic": subscription.topic,
                    "hub.lease_seconds": "2000",
                },
            )
        )

        subscription.refresh_from_db()

        assert subscription.expires

    @pytest.mark.django_db
    def test_get_denied(self, client, subscription):
        assert_ok(
            client.get(
                subscription.get_callback_url(),
                {
                    "hub.mode": "denied",
                    "hub.challenge": "OK",
                    "hub.topic": subscription.topic,
                    "hub.lease_seconds": "2000",
                },
            )
        )

        subscription.refresh_from_db()

        assert subscription.expires is None

    @pytest.mark.django_db
    def test_get_invalid_topic(self, client, subscription):
        assert_not_found(
            client.get(
                subscription.get_callback_url(),
                {
                    "hub.mode": "subscribe",
                    "hub.challenge": "OK",
                    "hub.topic": "https://wrong-topic.com/",
                    "hub.lease_seconds": "2000",
                },
            )
        )

        subscription.refresh_from_db()

        assert subscription.expires is None

    @pytest.mark.django_db
    def test_get_invalid_lease_seconds(self, client, subscription):
        assert_not_found(
            client.get(
                subscription.get_callback_url(),
                {
                    "hub.mode": "subscribe",
                    "hub.challenge": "OK",
                    "hub.topic": subscription.topic,
                    "hub.lease_seconds": "invalid",
                },
            )
        )

        subscription.refresh_from_db()

        assert subscription.expires is None

    @pytest.mark.django_db
    def test_get_missing_mode(self, client, subscription):
        assert_not_found(
            client.get(
                subscription.get_callback_url(),
                {
                    "hub.challenge": "OK",
                    "hub.topic": subscription.topic,
                    "hub.lease_seconds": "2000",
                },
            )
        )

        subscription.refresh_from_db()

        assert subscription.expires is None
