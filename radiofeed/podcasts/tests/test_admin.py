from __future__ import annotations

import http

from datetime import timedelta
from unittest import mock

import pytest

from django.contrib.admin.sites import AdminSite
from django.utils import timezone

from radiofeed.podcasts.admin import (
    ActiveFilter,
    CategoryAdmin,
    HttpStatusFilter,
    ParseResultFilter,
    PodcastAdmin,
    PromotedFilter,
    PubDateFilter,
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
        category.podcasts.set(podcasts)
        qs = category_admin.get_queryset(req)
        assert qs.count() == 1
        assert category_admin.num_podcasts(qs.first()) == 3


class TestPodcastAdmin:
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

    def test_parse_podcast_feed(self, mocker, podcast, podcast_admin, req):
        patched = mocker.patch("radiofeed.podcasts.admin.parse_feed")
        podcast_admin.parse_podcast_feed(req, podcast)
        patched.assert_called()

    def test_next_scheduled_update(self, mocker, podcast, podcast_admin):
        mocker.patch(
            "radiofeed.podcasts.admin.scheduler.next_scheduled_update",
            return_value=timezone.now() + timedelta(hours=3),
        )
        assert (
            podcast_admin.next_scheduled_update(podcast) == "2\xa0hours, 59\xa0minutes"
        )


class TestPubDateFilter:
    def test_none(self, podcasts, podcast_admin, req):
        PodcastFactory(pub_date=None)
        f = PubDateFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    def test_no(self, podcasts, podcast_admin, req):
        no_pub_date = PodcastFactory(pub_date=None)
        f = PubDateFilter(req, {"pub_date": "no"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == no_pub_date

    def test_yes(self, podcasts, podcast_admin, req):
        no_pub_date = PodcastFactory(pub_date=None)
        f = PubDateFilter(req, {"pub_date": "yes"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert no_pub_date not in qs


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


class TestHttpStatusFilter:
    def test_lookups(self, db, podcast_admin, req):
        PodcastFactory(http_status=http.HTTPStatus.OK)
        PodcastFactory(http_status=http.HTTPStatus.NOT_MODIFIED)

        f = HttpStatusFilter(req, {}, Podcast, podcast_admin)
        assert f.lookups(req, podcast_admin) == (
            (200, "200 OK"),
            (304, "304 NOT_MODIFIED"),
        )

    def test_filter(self, db, podcast_admin, req):
        podcast = PodcastFactory(http_status=http.HTTPStatus.OK)
        PodcastFactory(http_status=http.HTTPStatus.NOT_MODIFIED)

        f = HttpStatusFilter(req, {"http_status": "200"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == podcast

    def test_none(self, db, podcast_admin, req):
        PodcastFactory(http_status=http.HTTPStatus.OK)
        PodcastFactory(http_status=http.HTTPStatus.NOT_MODIFIED)

        f = HttpStatusFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 2


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


class TestParseResultFilter:
    def test_parse_result_none(self, db, podcast_admin, req):
        PodcastFactory(parse_result=Podcast.ParseResult.SUCCESS)
        podcast = PodcastFactory(parse_result=None)
        f = ParseResultFilter(req, {"parse_result": "none"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == podcast

    def test_parse_result_empty(self, db, podcast_admin, req):
        PodcastFactory(parse_result=Podcast.ParseResult.SUCCESS)
        PodcastFactory(parse_result=None)
        f = ParseResultFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 2

    def test_specific_parse_result(self, db, podcast_admin, req):
        podcast = PodcastFactory(parse_result=Podcast.ParseResult.SUCCESS)
        PodcastFactory(parse_result=None)
        PodcastFactory(parse_result=Podcast.ParseResult.NOT_MODIFIED)
        f = ParseResultFilter(
            req,
            {"parse_result": "success"},
            Podcast,
            podcast_admin,
        )
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == podcast
