from datetime import timedelta
from unittest import mock

import pytest
from django.contrib.admin.sites import AdminSite
from django.utils import timezone

from radiofeed.podcasts.admin import (
    ActiveFilter,
    CategoryAdmin,
    ParserErrorFilter,
    PodcastAdmin,
    PrivateFilter,
    PromotedFilter,
    PubDateFilter,
    ScheduledFilter,
    SubscribedFilter,
)
from radiofeed.podcasts.models import Category, Podcast
from radiofeed.podcasts.tests.factories import PodcastFactory, SubscriptionFactory


@pytest.fixture(scope="module")
def category_admin():
    return CategoryAdmin(Category, AdminSite())


@pytest.fixture(scope="module")
def podcast_admin():
    return PodcastAdmin(Podcast, AdminSite())


@pytest.fixture
def podcasts():
    return PodcastFactory.create_batch(
        3, active=True, promoted=False, parsed=timezone.now()
    )


@pytest.fixture
def req(rf):
    req = rf.get("/")
    req._messages = mock.Mock()
    return req


class TestCategoryAdmin:
    @pytest.mark.django_db
    def test_get_queryset(self, req, category_admin, podcasts, category):
        category.podcasts.set(podcasts)
        category = Category.objects.first()
        for podcast in podcasts:
            podcast.categories.add(category)
        qs = category_admin.get_queryset(req)
        assert category_admin.num_podcasts(qs.first()) == 3


class TestPodcastAdmin:
    @pytest.mark.django_db
    def test_get_queryset(self, podcasts, podcast_admin, req):
        qs = podcast_admin.get_queryset(req)
        assert qs.count() == 3

    @pytest.mark.django_db
    def test_make_promoted(self, podcasts, podcast_admin, req):
        podcast_admin.make_promoted(req, Podcast.objects.all())
        assert Podcast.objects.filter(promoted=True).count() == 3

    @pytest.mark.django_db
    def test_make_demoted(self, podcast_admin, req):
        PodcastFactory.create_batch(3, promoted=True)
        podcast_admin.make_demoted(req, Podcast.objects.all())
        assert Podcast.objects.filter(promoted=True).count() == 0

    @pytest.mark.django_db
    def test_get_search_results(self, podcasts, podcast_admin, req):
        podcast = PodcastFactory(title="Indie Hackers")
        qs, _ = podcast_admin.get_search_results(
            req, Podcast.objects.all(), "Indie Hackers"
        )
        assert qs.count() == 1
        assert qs.first() == podcast

    @pytest.mark.django_db
    def test_get_search_results_no_search_term(self, podcasts, podcast_admin, req):
        qs, _ = podcast_admin.get_search_results(req, Podcast.objects.all(), "")
        assert qs.count() == 3

    @pytest.mark.django_db
    def test_get_ordering_no_search_term(self, podcast_admin, req):
        ordering = podcast_admin.get_ordering(req)
        assert ordering == ["-parsed", "-pub_date"]

    @pytest.mark.django_db
    def test_get_ordering_search_term(self, podcast_admin, req):
        req.GET = {"q": "test"}
        ordering = podcast_admin.get_ordering(req)
        assert ordering == []

    @pytest.mark.django_db
    def test_next_scheduled_update(self, mocker, podcast, podcast_admin):
        mocker.patch(
            "radiofeed.podcasts.admin.Podcast.get_next_scheduled_update",
            return_value=timezone.now() + timedelta(hours=3),
        )
        assert (
            podcast_admin.next_scheduled_update(podcast) == "2\xa0hours, 59\xa0minutes"
        )

    @pytest.mark.django_db
    def test_next_scheduled_update_in_past(self, mocker, podcast, podcast_admin):
        mocker.patch(
            "radiofeed.podcasts.admin.Podcast.get_next_scheduled_update",
            return_value=timezone.now() + timedelta(hours=-3),
        )
        assert podcast_admin.next_scheduled_update(podcast) == "3\xa0hours ago"

    @pytest.mark.django_db
    def test_next_scheduled_update_inactive(self, mocker, podcast_admin):
        podcast = PodcastFactory(active=False)
        assert podcast_admin.next_scheduled_update(podcast) == "-"


class TestPubDateFilter:
    @pytest.mark.django_db
    def test_none(self, podcasts, podcast_admin, req):
        PodcastFactory(pub_date=None)
        f = PubDateFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    @pytest.mark.django_db
    def test_no(self, podcasts, podcast_admin, req):
        no_pub_date = PodcastFactory(pub_date=None)
        f = PubDateFilter(req, {"pub_date": ["no"]}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == no_pub_date

    @pytest.mark.django_db
    def test_yes(self, podcasts, podcast_admin, req):
        no_pub_date = PodcastFactory(pub_date=None)
        f = PubDateFilter(req, {"pub_date": ["yes"]}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert no_pub_date not in qs


class TestPromotedFilter:
    @pytest.mark.django_db
    def test_none(self, podcasts, podcast_admin, req):
        PodcastFactory(promoted=False)
        f = PromotedFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    @pytest.mark.django_db
    def test_promoted(self, podcasts, podcast_admin, req):
        promoted = PodcastFactory(promoted=True)
        f = PromotedFilter(req, {"promoted": ["yes"]}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == promoted


class TestPrivateFilter:
    @pytest.mark.django_db
    def test_none(self, podcasts, podcast_admin, req):
        PodcastFactory(private=False)
        f = PrivateFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    @pytest.mark.django_db
    def test_true(self, podcasts, podcast_admin, req):
        private = PodcastFactory(private=True)
        f = PrivateFilter(req, {"private": ["yes"]}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == private


class TestActiveFilter:
    @pytest.mark.django_db
    def test_none(self, podcasts, podcast_admin, req):
        PodcastFactory(active=False)
        f = ActiveFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    @pytest.mark.django_db
    def test_active(self, podcasts, podcast_admin, req):
        inactive = PodcastFactory(active=False)
        f = ActiveFilter(req, {"active": ["yes"]}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert inactive not in qs

    @pytest.mark.django_db
    def test_inactive(self, podcasts, podcast_admin, req):
        inactive = PodcastFactory(active=False)
        f = ActiveFilter(req, {"active": ["no"]}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert inactive in qs


class TestParserErrorFilter:
    @pytest.fixture
    def duplicate(self):
        return PodcastFactory(parser_error=Podcast.ParserError.DUPLICATE)

    @pytest.mark.django_db
    def test_all(self, podcasts, podcast_admin, req, duplicate):
        f = ParserErrorFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    @pytest.mark.django_db
    def test_duplicate(self, podcasts, podcast_admin, req, duplicate):
        f = ParserErrorFilter(
            req,
            {"parser_error": [Podcast.ParserError.DUPLICATE]},
            Podcast,
            podcast_admin,
        )
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert duplicate in qs


class TestScheduledFilter:
    @pytest.fixture
    def scheduled(self):
        return PodcastFactory(pub_date=None, parsed=None)

    @pytest.fixture
    def unscheduled(self):
        now = timezone.now()
        return PodcastFactory(pub_date=now, parsed=now, frequency=timedelta(hours=3))

    @pytest.mark.django_db
    def test_none(self, podcast_admin, req, scheduled, unscheduled):
        f = ScheduledFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 2

    @pytest.mark.django_db
    def test_true(self, podcast_admin, req, scheduled, unscheduled):
        f = ScheduledFilter(req, {"scheduled": ["yes"]}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == scheduled


class TestSubscribedFilter:
    @pytest.fixture
    def subscribed(self):
        return SubscriptionFactory().podcast

    @pytest.mark.django_db
    def test_none(self, podcasts, podcast_admin, req, subscribed):
        f = SubscribedFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    @pytest.mark.django_db
    def test_true(self, podcasts, podcast_admin, req, subscribed):
        f = SubscribedFilter(req, {"subscribed": ["yes"]}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == subscribed
