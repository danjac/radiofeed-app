import uuid

from unittest import mock

import pytest

from django.contrib.admin.sites import AdminSite
from django.utils import timezone

from jcasts.podcasts.admin import (
    ActiveFilter,
    PodcastAdmin,
    PromotedFilter,
    PubDateFilter,
    WebSubFilter,
)
from jcasts.podcasts.factories import PodcastFactory
from jcasts.podcasts.models import Podcast


@pytest.fixture(scope="class")
def admin():
    return PodcastAdmin(Podcast, AdminSite())


@pytest.fixture
def podcasts(db):
    return PodcastFactory.create_batch(
        3, active=True, promoted=False, scheduled=timezone.now()
    )


@pytest.fixture
def req(rf):
    req = rf.get("/")
    req._messages = mock.Mock()
    return req


class TestPodcastAdmin:
    def test_source(self, podcasts, admin):
        assert admin.source(podcasts[0]) == podcasts[0].get_domain()

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
        assert ordering == ["-pub_date"]

    def test_get_ordering_search_term(self, admin, req):
        req.GET = {"q": "test"}
        ordering = admin.get_ordering(req)
        assert ordering == []

    def test_reactivate(self, podcasts, admin, req):
        PodcastFactory(active=False)
        admin.reactivate(req, Podcast.objects.all())
        assert Podcast.objects.filter(active=True).count() == 4

    def test_parse_podcast_feeds(self, podcast, admin, req, mocker):
        mock_task = mocker.patch("jcasts.podcasts.feed_parser.parse_feed_fast")
        admin.parse_podcast_feeds(req, Podcast.objects.all())
        mock_task.assert_called_with(podcast)

    def test_reverify_websub_feeds(self, db, admin, req, mocker):
        podcast = PodcastFactory(
            websub_token=uuid.uuid4(), websub_hub="https://pubsubhubbub.com"
        )
        mock_task = mocker.patch("jcasts.podcasts.websub.subscribe.delay")
        admin.reverify_websub_feeds(req, Podcast.objects.all())
        mock_task.assert_called_with(podcast.id, reverify=True)


class TestPubDateFilter:
    def test_pub_date_filter_none(self, podcasts, admin, req):
        PodcastFactory(pub_date=None)
        f = PubDateFilter(req, {}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_pub_date_filter_false(self, podcasts, admin, req):
        no_pub_date = PodcastFactory(pub_date=None)
        f = PubDateFilter(req, {"pub_date": "no"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == no_pub_date

    def test_pub_date_filter_true(self, podcasts, admin, req):
        no_pub_date = PodcastFactory(pub_date=None)
        f = PubDateFilter(req, {"pub_date": "yes"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert no_pub_date not in qs


class TestActiveFilter:
    def test_active_filter_none(self, podcasts, admin, req):
        PodcastFactory(active=False)
        f = ActiveFilter(req, {}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_active_filter_false(self, podcasts, admin, req):
        inactive = PodcastFactory(active=False)
        f = ActiveFilter(req, {"active": "no"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == inactive

    def test_active_filter_true(self, podcasts, admin, req):
        inactive = PodcastFactory(active=False)
        f = ActiveFilter(req, {"active": "yes"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert inactive not in qs

    def test_promoted_filter_none(self, podcasts, admin, req):
        PodcastFactory(promoted=False)
        f = PromotedFilter(req, {}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_promoted_filter_true(self, podcasts, admin, req):
        promoted = PodcastFactory(promoted=True)
        f = PromotedFilter(req, {"promoted": "yes"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == promoted


class TestWebSubFilter:
    hub = "https://pubsubhubbub.appspot.com/"

    def test_websub_filter_subscribed(self, podcasts, admin, req):
        subscribed = PodcastFactory(
            websub_subscribed=timezone.now(), websub_hub=self.hub
        )
        f = WebSubFilter(req, {"websub": "subscribed"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == subscribed

    def test_websub_filter_requested(self, podcasts, admin, req):
        requested = PodcastFactory(websub_requested=timezone.now(), websub_hub=self.hub)
        f = WebSubFilter(req, {"websub": "requested"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == requested

    def test_websub_filter_pending(self, podcasts, admin, req):
        PodcastFactory(websub_subscribed=timezone.now(), websub_hub=self.hub)
        PodcastFactory(websub_requested=timezone.now(), websub_hub=self.hub)
        pending = PodcastFactory(websub_hub=self.hub)
        f = WebSubFilter(req, {"websub": "pending"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert pending in qs

    def test_websub_filter_failed(self, podcasts, admin, req):
        PodcastFactory(websub_subscribed=timezone.now(), websub_hub=self.hub)
        PodcastFactory(websub_requested=timezone.now(), websub_hub=self.hub)
        PodcastFactory(websub_hub=self.hub)
        failed = PodcastFactory(websub_exception="oops", websub_hub=self.hub)
        f = WebSubFilter(req, {"websub": "failed"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert failed in qs

    def test_websub_filter_none(self, podcasts, admin, req):
        subscribed = PodcastFactory(
            websub_subscribed=timezone.now(), websub_hub=self.hub
        )
        requested = PodcastFactory(websub_requested=timezone.now(), websub_hub=self.hub)
        pending = PodcastFactory(websub_hub=self.hub)
        f = WebSubFilter(req, {"websub": "none"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert subscribed not in qs
        assert requested not in qs
        assert pending not in qs

    def test_websub_filter_all(self, podcasts, admin, req):
        PodcastFactory(websub_subscribed=timezone.now(), websub_hub=self.hub)
        PodcastFactory(websub_requested=timezone.now(), websub_hub=self.hub)
        f = WebSubFilter(req, {}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 5
