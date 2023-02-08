from __future__ import annotations

import http

import pytest

from django.urls import reverse

from radiofeed.websub.factories import create_subscription


class TestWebsubCallback:
    @pytest.fixture
    def subscription(self, db):
        return create_subscription()

    @pytest.fixture
    def feed_parser(self, mocker):
        return mocker.patch("radiofeed.feedparser.feed_parser.FeedParser.parse")

    def get_url(self, subscription):
        return reverse("websub:callback", args=[subscription.id])

    def test_post(self, client, mocker, feed_parser, subscription):
        mocker.patch("radiofeed.websub.subscriber.check_signature", return_value=True)

        response = client.post(self.get_url(subscription))
        assert response.status_code == http.HTTPStatus.NO_CONTENT

        feed_parser.assert_called()

    def test_post_invalid_signature(self, client, mocker, feed_parser, subscription):
        mocker.patch("radiofeed.websub.subscriber.check_signature", return_value=False)

        response = client.post(self.get_url(subscription))
        assert response.status_code == http.HTTPStatus.NO_CONTENT

        feed_parser.assert_not_called()

    def test_get(self, client, subscription):
        response = client.get(
            self.get_url(subscription),
            {
                "hub.mode": "subscribe",
                "hub.challenge": "OK",
                "hub.topic": subscription.topic,
                "hub.lease_seconds": "2000",
            },
        )

        assert response.status_code == http.HTTPStatus.OK

        subscription.refresh_from_db()

        assert subscription.mode == "subscribe"
        assert subscription.verified
        assert subscription.expires

    def test_get_invalid_topic(self, client, subscription):
        response = client.get(
            self.get_url(subscription),
            {
                "hub.mode": "subscribe",
                "hub.challenge": "OK",
                "hub.topic": "https://wrong-topic.com/",
                "hub.lease_seconds": "2000",
            },
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND

        subscription.refresh_from_db()

        assert subscription.mode == ""
        assert subscription.verified is None

    def test_get_invalid_lease_seconds(self, client, subscription):
        response = client.get(
            self.get_url(subscription),
            {
                "hub.mode": "subscribe",
                "hub.challenge": "OK",
                "hub.topic": subscription.topic,
                "hub.lease_seconds": "invalid",
            },
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND

        subscription.refresh_from_db()

        assert subscription.mode == ""
        assert subscription.verified is None

    def test_get_missing_mode(self, client, subscription):
        response = client.get(
            self.get_url(subscription),
            {
                "hub.challenge": "OK",
                "hub.topic": subscription.topic,
                "hub.lease_seconds": "2000",
            },
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND

        subscription.refresh_from_db()

        assert subscription.mode == ""
        assert subscription.verified is None
