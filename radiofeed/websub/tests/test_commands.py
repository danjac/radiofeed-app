import pytest
import requests
from django.core.management import call_command

from radiofeed.websub.factories import create_subscription


class TestSubscribeWebsubFeeds:
    @pytest.fixture
    def subscribe(self, mocker):
        return mocker.patch("radiofeed.websub.models.Subscription.subscribe")

    @pytest.fixture
    def subscription(self):
        return create_subscription()

    @pytest.mark.django_db(transaction=True)
    def test_subscribe(self, subscribe, subscription):
        call_command("subscribe_websub_feeds", limit=200)
        subscribe.assert_called()

    @pytest.mark.django_db(transaction=True)
    def test_exception(self, mocker, subscription):
        subscribe = mocker.patch(
            "radiofeed.websub.models.Subscription.subscribe",
            side_effect=requests.HTTPError("oops"),
        )

        call_command("subscribe_websub_feeds", limit=200)
        subscribe.assert_called()
