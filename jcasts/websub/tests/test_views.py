import hmac

import pytest

from django.urls import reverse
from django.utils import timezone

from jcasts.shared.assertions import assert_no_content, assert_not_found, assert_ok
from jcasts.websub.models import Subscription


class TestWebSubCallback:
    def test_post_ok(self, client, subscription, mock_feed_queue):
        body = b"testme"

        sig = hmac.new(
            subscription.secret.hex.encode("utf-8"), body, "sha1"
        ).hexdigest()

        resp = client.post(
            self.url(subscription),
            body,
            content_type="application/xml",
            HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
        )
        assert_no_content(resp)

        assert subscription.podcast_id in mock_feed_queue.enqueued

    def test_post_missing_sig(self, client, subscription, mock_feed_queue):

        resp = client.post(
            self.url(subscription),
            b"testme",
            content_type="application/xml",
        )
        assert_no_content(resp)

        assert subscription.podcast_id not in mock_feed_queue.enqueued

    def test_get_topic_mismatch(self, client, subscription):

        resp = client.get(
            self.url(subscription),
            {
                "hub.mode": "subscribe",
                "hub.challenge": "ok",
                "hub.topic": "https://other-topic.com",
                "hub.lease_seconds": 3600,
            },
        )

        assert_not_found(resp)

        subscription.refresh_from_db()

        assert subscription.status is None
        assert subscription.status_changed is None

    def test_get_subscribe(self, client, subscription):

        resp = client.get(
            self.url(subscription),
            {
                "hub.mode": "subscribe",
                "hub.challenge": "ok",
                "hub.topic": subscription.topic,
                "hub.lease_seconds": 3600,
            },
        )

        assert_ok(resp)

        subscription.refresh_from_db()

        assert subscription.status == Subscription.Status.SUBSCRIBED
        assert subscription.status_changed
        assert (subscription.expires - timezone.now()).total_seconds() == pytest.approx(
            3600, 1
        )

    def test_get_missing_mode(self, client, subscription):

        resp = client.get(
            self.url(subscription),
            {
                "hub.challenge": "ok",
                "hub.topic": subscription.topic,
                "hub.lease_seconds": 3600,
            },
        )

        assert_not_found(resp)

        subscription.refresh_from_db()

        assert subscription.status is None
        assert subscription.status_changed is None
        assert subscription.exception

    def test_get_missing_invalid_mode(self, client, subscription):

        resp = client.get(
            self.url(subscription),
            {
                "hub.mode": "invalid",
                "hub.challenge": "ok",
                "hub.topic": subscription.topic,
                "hub.lease_seconds": 3600,
            },
        )

        assert_not_found(resp)

        subscription.refresh_from_db()

        assert subscription.status is None
        assert subscription.status_changed is None
        assert subscription.exception

    def test_get_missing_challenge(self, client, subscription):

        resp = client.get(
            self.url(subscription),
            {
                "hub.mode": "subscribe",
                "hub.topic": subscription.topic,
                "hub.lease_seconds": 3600,
            },
        )

        assert_not_found(resp)

        subscription.refresh_from_db()

        assert subscription.status is None
        assert subscription.status_changed is None
        assert subscription.exception

    def test_get_missing_lease_seconds(self, client, subscription):

        resp = client.get(
            self.url(subscription),
            {
                "hub.mode": "subscribe",
                "hub.challenge": "ok",
                "hub.topic": subscription.topic,
            },
        )

        assert_not_found(resp)

        subscription.refresh_from_db()

        assert subscription.status is None
        assert subscription.status_changed is None
        assert subscription.exception

    def test_get_unsubscribe(self, client, subscription):

        resp = client.get(
            self.url(subscription),
            {
                "hub.mode": "unsubscribe",
                "hub.challenge": "ok",
                "hub.topic": subscription.topic,
            },
        )

        assert_ok(resp)
        assert resp.content == b"ok"

        subscription.refresh_from_db()

        assert subscription.status == Subscription.Status.UNSUBSCRIBED
        assert subscription.status_changed
        assert subscription.expires is None

    def url(self, subscription):
        return reverse("websub:callback", args=[subscription.id])
