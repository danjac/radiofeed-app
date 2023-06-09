import pytest
from django.contrib.admin.sites import AdminSite
from django.utils import timezone

from radiofeed.websub import subscriber
from radiofeed.websub.admin import (
    ConfirmedFilter,
    FailedFilter,
    PendingFilter,
    PingedFilter,
    SubscribedFilter,
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


class TestPendingFilter:
    @pytest.mark.django_db
    def test_all(self, req, subscription_admin):
        create_subscription()
        create_subscription(mode=subscriber.SUBSCRIBE)
        f = PendingFilter(req, {}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 2

    @pytest.mark.django_db
    def test_pending(self, req, subscription_admin):
        pending = create_subscription()
        create_subscription(mode=subscriber.SUBSCRIBE)
        f = PendingFilter(req, {"pending": "yes"}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 1
        assert qs.first() == pending


class TestSubscribedFilter:
    @pytest.mark.django_db
    def test_all(self, req, subscription_admin):
        create_subscription()
        create_subscription(mode=subscriber.SUBSCRIBE)
        f = SubscribedFilter(req, {}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 2

    @pytest.mark.django_db
    def test_subscribed(self, req, subscription_admin):
        create_subscription()
        subscribed = create_subscription(mode=subscriber.SUBSCRIBE)
        f = SubscribedFilter(
            req, {"subscribed": "yes"}, Subscription, subscription_admin
        )
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 1
        assert qs.first() == subscribed


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


class TestFailedFilter:
    @pytest.mark.django_db
    def test_all(self, req, subscription_admin):
        create_subscription()
        create_subscription(num_retries=3)
        f = FailedFilter(req, {}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 2

    @pytest.mark.django_db
    def test_failed(self, req, subscription_admin):
        create_subscription()
        failed = create_subscription(num_retries=3)
        f = FailedFilter(req, {"failed": "yes"}, Subscription, subscription_admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 1
        assert qs.first() == failed
