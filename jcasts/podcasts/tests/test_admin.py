from datetime import timedelta
from unittest import mock

import pytest

from django.contrib.admin.sites import AdminSite
from django.utils import timezone

from jcasts.podcasts.admin import (
    ActiveFilter,
    FollowedFilter,
    PodcastAdmin,
    PodpingFilter,
    PromotedFilter,
    PubDateFilter,
    ResultFilter,
    SchedulingFilter,
)
from jcasts.podcasts.factories import FollowFactory, PodcastFactory
from jcasts.podcasts.models import Podcast


@pytest.fixture(scope="class")
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
    def test_scheduled_queued(self, admin):
        assert admin.scheduled(Podcast(queued=timezone.now())) == "Queued"

    def test_scheduled_pending(self, admin):
        now = timezone.now()
        assert (
            admin.scheduled(
                Podcast(pub_date=now - timedelta(days=1), frequency=timedelta(hours=3))
            )
            == "Pending"
        )

    def test_scheduled_value(self, admin):
        now = timezone.now()
        assert (
            admin.scheduled(
                Podcast(
                    pub_date=now - timedelta(days=1),
                    frequency=timedelta(days=3),
                    parsed=timedelta(days=1),
                )
            )
            == "1\xa0day, 23\xa0hours"
        )

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

    def test_parse_podcast_feeds(self, podcast, admin, req, mock_parse_podcast_feed):
        admin.parse_podcast_feeds(req, Podcast.objects.all())
        mock_parse_podcast_feed.assert_called_with(podcast.id)
        assert Podcast.objects.filter(queued__isnull=False).count() == 1

    def test_reactivate_podcasts(self, db, admin, req):

        PodcastFactory(active=False)
        PodcastFactory(active=True, num_failures=4)

        admin.reactivate_podcasts(req, Podcast.objects.all())

        assert Podcast.objects.inactive().count() == 0

    def test_reactivate_podcasts_none_selected(self, podcast, admin, req):
        PodcastFactory(active=False)
        admin.reactivate_podcasts(req, Podcast.objects.active())
        assert Podcast.objects.inactive().count() == 1

    def test_parse_podcast_feed(self, podcast, admin, req, mock_parse_podcast_feed):
        admin.parse_podcast_feed(req, podcast)
        mock_parse_podcast_feed.assert_called_with(podcast.id)
        assert Podcast.objects.filter(queued__isnull=False).count() == 1

    def test_parse_podcast_feed_queued(
        self, podcast, admin, req, mock_parse_podcast_feed
    ):
        podcast.queued = timezone.now()
        admin.parse_podcast_feed(req, podcast)
        mock_parse_podcast_feed.assert_not_called()

    def test_parse_podcast_feed_inactive(
        self, podcast, admin, req, mock_parse_podcast_feed
    ):
        podcast.active = False
        admin.parse_podcast_feed(req, podcast)
        mock_parse_podcast_feed.assert_not_called()


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


class TestPodpingFilter:
    def test_none(self, podcasts, admin, req):
        PodcastFactory(podping=False)
        f = PodpingFilter(req, {}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_true(self, podcasts, admin, req):
        podping = PodcastFactory(podping=True)
        f = PodpingFilter(req, {"podping": "yes"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == podping

    def test_false(self, podcasts, admin, req):
        podping = PodcastFactory(podping=True)
        f = PodpingFilter(req, {"podping": "no"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert podping not in qs


class TestSchedulingFilter:
    def test_none(self, podcasts, admin, req):
        PodcastFactory(queued=timezone.now())
        PodcastFactory(active=False)
        f = SchedulingFilter(req, {}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 5

    def test_scheduled(self, podcasts, admin, req):
        queued = PodcastFactory(queued=timezone.now())
        f = SchedulingFilter(req, {"scheduling": "scheduled"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert queued not in qs

    def test_queued(self, podcasts, admin, req):
        queued = PodcastFactory(queued=timezone.now())
        f = SchedulingFilter(req, {"scheduling": "queued"}, Podcast, admin)
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


class TestFollowedFilter:
    def test_followed_filter_none(self, podcasts, admin, req):
        FollowFactory()
        f = FollowedFilter(req, {}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_promoted_filter_true(self, podcasts, admin, req):
        followed = FollowFactory().podcast
        f = FollowedFilter(req, {"followed": "yes"}, Podcast, admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == followed
