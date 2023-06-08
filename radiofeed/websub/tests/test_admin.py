import pytest
from django.contrib.admin.sites import AdminSite

from radiofeed.websub import subscriber
from radiofeed.websub.admin import ModeFilter, SubscriptionAdmin
from radiofeed.websub.factories import create_subscription
from radiofeed.websub.models import Subscription


@pytest.fixture
def req(rf):
    return rf.get("/")


@pytest.fixture
def subscription_admin():
    return SubscriptionAdmin(Subscription, AdminSite())


class TestModeFilter:
    @pytest.mark.django_db
    def test_all(self, req, subscription_admin):
        create_subscription()
        create_subscription(mode=subscriber.SUBSCRIBE)
        f = ModeFilter(req, {}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 2

    @pytest.mark.django_db
    def test_subscribed(self, req, subscription_admin):
        create_subscription()
        subscribed = create_subscription(mode=subscriber.SUBSCRIBE)
        f = ModeFilter(req, {"mode": "subscribe"}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 1
        assert qs.first() == subscribed

    @pytest.mark.django_db
    def test_unsubscribed(self, req, subscription_admin):
        create_subscription()
        unsubscribed = create_subscription(mode=subscriber.UNSUBSCRIBE)
        f = ModeFilter(req, {"mode": "unsubscribe"}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 1
        assert qs.first() == unsubscribed

    @pytest.mark.django_db
    def test_none(self, req, subscription_admin):
        none = create_subscription()
        create_subscription(mode=subscriber.SUBSCRIBE)
        f = ModeFilter(req, {"mode": "none"}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 1
        assert qs.first() == none
