import pytest
from django.contrib.admin.sites import AdminSite
from django.utils import timezone

from radiofeed.websub import subscriber
from radiofeed.websub.admin import (
    ConfirmedFilter,
    PingedFilter,
    StatusFilter,
    SubscriptionAdmin,
)
from radiofeed.websub.factories import create_subscription
from radiofeed.websub.models import Subscription


@pytest.fixture
def req(rf):
    return rf.get("/")


@pytest.fixture
def subscription_admin():
    return SubscriptionAdmin(Subscription, AdminSite())


class TestStatusFilter:
    @pytest.fixture
    def subscribed(self):
        return create_subscription(mode=subscriber.SUBSCRIBE)

    @pytest.fixture
    def pending(self):
        return create_subscription(mode="")

    @pytest.fixture
    def failed(self):
        return create_subscription(num_retries=3)

    @pytest.mark.django_db
    def test_all(self, req, subscription_admin, subscribed, pending, failed):
        f = StatusFilter(req, {}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 3

    @pytest.mark.django_db
    def test_subscribed(self, req, subscription_admin, subscribed, pending, failed):
        f = StatusFilter(
            req, {"status": "subscribed"}, Subscription, subscription_admin
        )
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 1
        assert qs.first() == subscribed

    @pytest.mark.django_db
    def test_failed(self, req, subscription_admin, subscribed, pending, failed):
        f = StatusFilter(req, {"status": "failed"}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 1
        assert qs.first() == failed

    @pytest.mark.django_db
    def test_pending(self, req, subscription_admin, subscribed, pending, failed):
        f = StatusFilter(req, {"status": "pending"}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 1
        assert qs.first() == pending


class TestConfirmedFilter:
    @pytest.mark.django_db
    def test_all(self, req, subscription_admin):
        create_subscription()
        create_subscription(confirmed=timezone.now())
        f = ConfirmedFilter(req, {}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 2

    @pytest.mark.django_db
    def test_confirmed(self, req, subscription_admin):
        create_subscription()
        confirmed = create_subscription(confirmed=timezone.now())
        f = ConfirmedFilter(req, {"confirmed": "yes"}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 1
        assert qs.first() == confirmed


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
