from unittest import mock

import pytest

from django.contrib.admin.sites import AdminSite

from radiofeed.podcasts.admin import (
    ActiveFilter,
    CategoryAdmin,
    PodcastAdmin,
    PromotedFilter,
    PubDateFilter,
    ResultFilter,
    SubscribedFilter,
)
from radiofeed.podcasts.factories import PodcastFactory, SubscriptionFactory
from radiofeed.podcasts.models import Category, Podcast


@pytest.fixture(scope="module")
def category_admin():
    return CategoryAdmin(Category, AdminSite())


@pytest.fixture(scope="module")
def podcast_admin():
    return PodcastAdmin(Podcast, AdminSite())


@pytest.fixture
def podcasts(db):
    return PodcastFactory.create_batch(3, active=True, promoted=False)


@pytest.fixture
def req(rf):
    req = rf.get("/")
    req._messages = mock.Mock()
    return req


class TestCategoryAdmin:
    def test_get_queryset(self, req, category_admin, podcasts, category):
        category.podcast_set.set(podcasts)
        qs = category_admin.get_queryset(req)
        assert qs.count() == 1
        assert category_admin.num_podcasts(qs.first()) == 3


class TestPodcastAdmin:
    @pytest.fixture
    def mock_parse_feed(self, mocker):
        return mocker.patch("radiofeed.podcasts.admin.parse_podcast_feed")

    def test_get_search_results(self, podcasts, podcast_admin, req):
        podcast = PodcastFactory(title="Indie Hackers")
        qs, _ = podcast_admin.get_search_results(
            req, Podcast.objects.all(), "Indie Hackers"
        )
        assert qs.count() == 1
        assert qs.first() == podcast

    def test_get_search_results_no_search_term(self, podcasts, podcast_admin, req):
        qs, _ = podcast_admin.get_search_results(req, Podcast.objects.all(), "")
        assert qs.count() == 3

    def test_get_ordering_no_search_term(self, podcast_admin, req):
        ordering = podcast_admin.get_ordering(req)
        assert ordering == ["-parsed", "-pub_date"]

    def test_get_ordering_search_term(self, podcast_admin, req):
        req.GET = {"q": "test"}
        ordering = podcast_admin.get_ordering(req)
        assert ordering == []

    def test_parse_podcast_feeds(self, mock_parse_feed, podcast, podcast_admin, req):
        podcast_admin.parse_podcast_feeds(req, Podcast.objects.all())
        mock_parse_feed.map.assert_called()

    def test_parse_podcast_feed(self, mock_parse_feed, podcast, podcast_admin, req):
        podcast_admin.parse_podcast_feed(req, podcast)
        mock_parse_feed.assert_called_with(podcast.id)


class TestResultFilter:
    def test_no_filter(self, podcasts, podcast_admin, req):
        PodcastFactory(result=Podcast.Result.NOT_MODIFIED)
        f = ResultFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_none(self, podcasts, podcast_admin, req):
        podcast = PodcastFactory(result=Podcast.Result.NOT_MODIFIED)
        f = ResultFilter(req, {"result": "none"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert podcast not in qs

    def test_not_modified(self, podcasts, podcast_admin, req):
        podcast = PodcastFactory(result=Podcast.Result.NOT_MODIFIED)
        f = ResultFilter(
            req, {"result": Podcast.Result.NOT_MODIFIED}, Podcast, podcast_admin
        )
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert podcast in qs


class TestPubDateFilter:
    def test_none(self, podcasts, podcast_admin, req):
        PodcastFactory(pub_date=None)
        f = PubDateFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_false(self, podcasts, podcast_admin, req):
        no_pub_date = PodcastFactory(pub_date=None)
        f = PubDateFilter(req, {"pub_date": "no"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == no_pub_date

    def test_true(self, podcasts, podcast_admin, req):
        no_pub_date = PodcastFactory(pub_date=None)
        f = PubDateFilter(req, {"pub_date": "yes"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert no_pub_date not in qs

    def test_new(self, podcasts, podcast_admin, req):
        new = PodcastFactory(pub_date=None, parsed=None)
        f = PubDateFilter(req, {"pub_date": "new"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert new in qs


class TestPromotedFilter:
    def test_none(self, podcasts, podcast_admin, req):
        PodcastFactory(promoted=False)
        f = PromotedFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_true(self, podcasts, podcast_admin, req):
        promoted = PodcastFactory(promoted=True)
        f = PromotedFilter(req, {"promoted": "yes"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == promoted


class TestActiveFilter:
    def test_none(self, podcasts, podcast_admin, req):
        PodcastFactory(active=False)
        f = ActiveFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_active(self, podcasts, podcast_admin, req):
        inactive = PodcastFactory(active=False)
        f = ActiveFilter(req, {"active": "yes"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert inactive not in qs

    def test_inactive(self, podcasts, podcast_admin, req):
        inactive = PodcastFactory(active=False)
        f = ActiveFilter(req, {"active": "no"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert inactive in qs


class TestSubscribedFilter:
    def test_subscribed_filter_none(self, podcasts, podcast_admin, req):
        SubscriptionFactory()
        f = SubscribedFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_subscribed_filter_true(self, podcasts, podcast_admin, req):
        subscribed = SubscriptionFactory().podcast
        f = SubscribedFilter(req, {"subscribed": "yes"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == subscribed
