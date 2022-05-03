from datetime import timedelta
from unittest import mock

import pytest

from django.contrib.admin.sites import AdminSite
from django.utils import timezone

from podtracker.podcasts.admin import (
    ActiveFilter,
    PodcastAdmin,
    PromotedFilter,
    PubDateFilter,
    QueuedFilter,
    ResultFilter,
    SubscribedFilter,
)
from podtracker.podcasts.factories import PodcastFactory, SubscriptionFactory
from podtracker.podcasts.models import Podcast


@pytest.fixture(scope="module")
def admin():
    return PodcastAdmin(Podcast, AdminSite())


@pytest.fixture
def podcasts(db):
    return PodcastFactory.create_batch(3, active=True, promoted=False)


@pytest.fixture
def req(rf):
    req = rf.get("/")
    req._messages = mock.Mock()
    return req


class TestPodcastAdmin:
    @pytest.fixture
    def mock_parse_feed(self, mocker):
        class MockParseFeed:
            def __init__(self, podcast_id):
                print("setting podcast id", podcast_id)
                self.podcast_id = podcast_id

            def __call__(self):
                print("calling mock parse...")
                ...

        mocker.patch("podtracker.podcasts.admin.parse_podcast_feed", MockParseFeed)

    def test_get_search_results(self, podcasts, admin, req):
        podcast = PodcastFactory(title="Indie Hackers")
        qs, _ = admin.get_search_results(req, Podcast.objects.all(), "Indie Hackers")
        assert qs.count() == 1
        assert qs.first() == podcast

    def test_get_search_results_no_search_term(self, podcasts, admin, req):
        qs, _ = admin.get_search_results(req, Podcast.objects.all(), "")
        assert qs.count() == 3

    def test_get_ordering_no_search_term(self, admin, req):
        ordering = admin.get_ordering(req)
        assert ordering == ["-parsed", "-pub_date"]

    def test_get_ordering_search_term(self, admin, req):
        req.GET = {"q": "test"}
        ordering = admin.get_ordering(req)
        assert ordering == []

    def test_dequeue(self, db, admin, req):
        podcast = PodcastFactory(queued=timezone.now())
        admin.dequeue(req, Podcast.objects.all())
        podcast.refresh_from_db()
        assert podcast.queued is None

    def test_parse_podcast_feeds(self, mock_parse_feed, podcast, admin, req):
        admin.parse_podcast_feeds(req, Podcast.objects.all())
        assert Podcast.objects.filter(queued__isnull=False).count() == 1

    def test_parse_podcast_feed(self, mock_parse_feed, podcast, admin, req):

        admin.parse_podcast_feed(req, podcast)

        assert Podcast.objects.filter(queued__isnull=False).count() == 1

    def test_parse_podcast_feed_queued(self, mock_parse_feed, podcast, admin, req):
        podcast.queued = timezone.now()
        admin.parse_podcast_feed(req, podcast)

    def test_parse_podcast_feed_inactive(self, mock_parse_feed, podcast, admin, req):
        podcast.active = False
        admin.parse_podcast_feed(req, podcast)


class TestResultFilter:
    def test_no_filter(self, podcasts, admin, req):
        PodcastFactory(result=Podcast.Result.NOT_MODIFIED)
        f = ResultFilter(req, {}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_none(self, podcasts, admin, req):
        podcast = PodcastFactory(result=Podcast.Result.NOT_MODIFIED)
        f = ResultFilter(req, {"result": "none"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert podcast not in qs

    def test_not_modified(self, podcasts, admin, req):
        podcast = PodcastFactory(result=Podcast.Result.NOT_MODIFIED)
        f = ResultFilter(req, {"result": Podcast.Result.NOT_MODIFIED}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert podcast in qs


class TestPubDateFilter:
    def test_none(self, podcasts, admin, req):
        PodcastFactory(pub_date=None)
        f = PubDateFilter(req, {}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_false(self, podcasts, admin, req):
        no_pub_date = PodcastFactory(pub_date=None)
        f = PubDateFilter(req, {"pub_date": "no"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == no_pub_date

    def test_true(self, podcasts, admin, req):
        no_pub_date = PodcastFactory(pub_date=None)
        f = PubDateFilter(req, {"pub_date": "yes"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert no_pub_date not in qs

    def test_new(self, podcasts, admin, req):
        new = PodcastFactory(pub_date=None, parsed=None)
        f = PubDateFilter(req, {"pub_date": "new"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert new in qs

    def test_recent(self, db, admin, req):
        now = timezone.now()
        PodcastFactory(pub_date=now - timedelta(days=30))
        recent = PodcastFactory(pub_date=now - timedelta(days=3))
        f = PubDateFilter(req, {"pub_date": "recent"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert recent in qs

    def test_sporadic(self, db, admin, req):
        now = timezone.now()
        sporadic = PodcastFactory(pub_date=now - timedelta(days=30))
        PodcastFactory(pub_date=now - timedelta(days=3))
        f = PubDateFilter(req, {"pub_date": "sporadic"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert sporadic in qs


class TestPromotedFilter:
    def test_none(self, podcasts, admin, req):
        PodcastFactory(promoted=False)
        f = PromotedFilter(req, {}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_true(self, podcasts, admin, req):
        promoted = PodcastFactory(promoted=True)
        f = PromotedFilter(req, {"promoted": "yes"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == promoted


class TestQueuedFilter:
    def test_none(self, podcasts, admin, req):
        PodcastFactory(queued=timezone.now())
        f = QueuedFilter(req, {}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_queued(self, podcasts, admin, req):
        queued = PodcastFactory(queued=timezone.now())
        f = QueuedFilter(req, {"queued": "yes"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert queued in qs


class TestActiveFilter:
    def test_none(self, podcasts, admin, req):
        PodcastFactory(active=False)
        f = ActiveFilter(req, {}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_active(self, podcasts, admin, req):
        inactive = PodcastFactory(active=False)
        f = ActiveFilter(req, {"active": "yes"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert inactive not in qs

    def test_inactive(self, podcasts, admin, req):
        inactive = PodcastFactory(active=False)
        f = ActiveFilter(req, {"active": "no"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert inactive in qs


class TestSubscribedFilter:
    def test_subscribed_filter_none(self, podcasts, admin, req):
        SubscriptionFactory()
        f = SubscribedFilter(req, {}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_promoted_filter_true(self, podcasts, admin, req):
        subscribed = SubscriptionFactory().podcast
        f = SubscribedFilter(req, {"subscribed": "yes"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == subscribed
