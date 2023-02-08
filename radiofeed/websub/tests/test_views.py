from __future__ import annotations

import http

from django.urls import reverse

from radiofeed.websub.factories import create_subscription
from radiofeed.websub.models import Subscription


class TestWebsubCallback:
    def get_url(self, subscription):
        return reverse("websub:callback", args=[subscription.id])

    def test_post(self, client, mocker, db):
        parser = mocker.patch("radiofeed.feedparser.feed_parser.FeedParser.parse")
        mocker.patch("radiofeed.websub.subscriber.check_signature", return_value=True)

        subscription = create_subscription(status=Subscription.Status.SUBSCRIBED)

        response = client.post(self.get_url(subscription))
        assert response.status_code == http.HTTPStatus.NO_CONTENT

        parser.assert_called()
