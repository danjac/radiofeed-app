class TestSubscriptionModel:
    def test_str(self, subscription):
        assert str(subscription) == subscription.topic

    def test_callback_url(self, subscription):
        assert (
            subscription.get_callback_url()
            == f"http://example.com/websub/{subscription.id}/"
        )
