from jcasts.websub.models import Subscription


class TestSubscriptionModel:
    def test_str(self, subscription):
        assert str(subscription) == subscription.topic

    def test_callback_url(self, subscription):
        assert (
            subscription.get_callback_url()
            == f"http://example.com/websub/{subscription.id}/"
        )

    def test_set_status(self):
        subscription = Subscription(status=None)
        assert subscription.set_status("subscribe") == Subscription.Status.SUBSCRIBED
        assert subscription.status == Subscription.Status.SUBSCRIBED
        assert subscription.status_changed is not None
