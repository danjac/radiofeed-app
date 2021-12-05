from datetime import timedelta

from django.core.management import call_command
from django.utils import timezone

from jcasts.websub.factories import SubscriptionFactory
from jcasts.websub.models import Subscription


class TestRenewSubscriptions:
    def test_command(self, db, mock_subscribe):
        SubscriptionFactory(
            status=Subscription.Status.SUBSCRIBED,
            expires=timezone.now() - timedelta(days=3),
        )
        call_command("renew_subscriptions")

        mock_subscribe.assert_called()
