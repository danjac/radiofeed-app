import pytest

from django.contrib.admin.sites import AdminSite

from jcasts.websub.admin import StatusFilter, SubscriptionAdmin
from jcasts.websub.factories import SubscriptionFactory
from jcasts.websub.models import Subscription


@pytest.fixture
def subscriptions(db):
    return SubscriptionFactory.create_batch(3)


@pytest.fixture
def req(rf):
    return rf.get("/")


@pytest.fixture(scope="class")
def admin():
    return SubscriptionAdmin(Subscription, AdminSite())


class TestStatusFilter:
    def test_no_filter(self, subscriptions, admin, req):
        SubscriptionFactory(status=Subscription.Status.SUBSCRIBED)
        f = StatusFilter(req, {}, Subscription, admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 4

    def test_none(self, subscriptions, admin, req):
        sub = SubscriptionFactory(status=Subscription.Status.SUBSCRIBED)
        f = StatusFilter(req, {"status": "none"}, Subscription, admin)
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 3
        assert sub not in qs

    def test_not_modified(self, subscriptions, admin, req):
        sub = SubscriptionFactory(status=Subscription.Status.SUBSCRIBED)
        f = StatusFilter(
            req, {"status": Subscription.Status.SUBSCRIBED}, Subscription, admin
        )
        qs = f.queryset(req, Subscription.objects.all())
        assert qs.count() == 1
        assert sub in qs
