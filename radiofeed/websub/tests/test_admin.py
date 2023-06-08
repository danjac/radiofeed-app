import pytest
from django.contrib.admin.sites import AdminSite
from django.utils import timezone

from radiofeed.websub import subscriber
from radiofeed.websub.admin import (
    ModeFilter,
    PingedFilter,
    RequestedFilter,
    SubscriptionAdmin,
    VerifiedFilter,
)
from radiofeed.websub.factories import create_subscription
from radiofeed.websub.models import Subscription


@pytest.fixture
def req(rf):
    return rf.get("/")


@pytest.fixture
def subscription_admin():
    return SubscriptionAdmin(Subscription, AdminSite())


class TestPingedFilter:
    @pytest.mark.django_db
    def test_all(self, req, subscription_admin):
        create_subscription()
        create_subscription(pinged=timezone.now())
        f = PingedFilter(req, {}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 2

    @pytest.mark.django_db
    def test_pinged(self, req, subscription_admin):
        create_subscription()
        pinged = create_subscription(pinged=timezone.now())
        f = PingedFilter(req, {"pinged": "yes"}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 1
        assert qs.first() == pinged


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


class TestVerifiedFilter:
    @pytest.mark.django_db
    def test_all(self, req, subscription_admin):
        create_subscription()
        create_subscription(verified=timezone.now())
        f = VerifiedFilter(req, {}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 2

    @pytest.mark.django_db
    def test_verified(self, req, subscription_admin):
        create_subscription()
        verified = create_subscription(verified=timezone.now())
        f = VerifiedFilter(req, {"verified": "yes"}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 1
        assert qs.first() == verified


class TestRequestedFilter:
    @pytest.mark.django_db
    def test_all(self, req, subscription_admin):
        create_subscription()
        create_subscription(requested=timezone.now())
        f = RequestedFilter(req, {}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 2

    @pytest.mark.django_db
    def test_requested(self, req, subscription_admin):
        create_subscription()
        requested = create_subscription(requested=timezone.now())
        f = RequestedFilter(req, {"requested": "yes"}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 1
        assert qs.first() == requested
