from unittest import mock

import pytest
from django.contrib.admin.sites import AdminSite
from django.utils import timezone

from listenfeed.podcasts.admin import (
    ActiveFilter,
    CategoryAdmin,
    ParserResultFilter,
    PodcastAdmin,
    PodcastTypeFilter,
    PrivateFilter,
    PromotedFilter,
    RecommendationAdmin,
    ScheduledFilter,
    SubscribedFilter,
    SubscriptionAdmin,
)
from listenfeed.podcasts.models import Category, Podcast, Recommendation, Subscription
from listenfeed.podcasts.tests.factories import (
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)


@pytest.fixture(scope="module")
def category_admin():
    return CategoryAdmin(Category, AdminSite())


@pytest.fixture(scope="module")
def podcast_admin():
    return PodcastAdmin(Podcast, AdminSite())


@pytest.fixture
def podcasts():
    return PodcastFactory.create_batch(3, active=True, parsed=timezone.now())


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
            "listenfeed.podcasts.admin.Podcast.get_next_scheduled_update",
            return_value=timezone.now() + timezone.timedelta(hours=3),
        )
        assert (
            podcast_admin.next_scheduled_update(podcast) == "2\xa0hours, 59\xa0minutes"
        )

    @pytest.mark.django_db
    def test_next_scheduled_update_in_past(self, mocker, podcast, podcast_admin):
        mocker.patch(
            "listenfeed.podcasts.admin.Podcast.get_next_scheduled_update",
            return_value=timezone.now() + timezone.timedelta(hours=-3),
        )
        assert podcast_admin.next_scheduled_update(podcast) == "3\xa0hours ago"

    @pytest.mark.django_db
    def test_next_scheduled_update_inactive(self, mocker, podcast_admin):
        podcast = PodcastFactory(active=False)
        assert podcast_admin.next_scheduled_update(podcast) == "-"


class TestPromotedFilter:
    @pytest.mark.django_db
    def test_none(self, podcasts, podcast_admin, req):
        f = PromotedFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3

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


class TestParserResultFilter:
    @pytest.fixture
    def duplicate(self):
        return PodcastFactory(
            parser_result=Podcast.ParserResult.DUPLICATE,
            parsed=timezone.now(),
        )

    @pytest.mark.django_db
    def test_all(self, podcasts, podcast_admin, req, duplicate):
        f = ParserResultFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    @pytest.mark.django_db
    def test_duplicate(self, podcasts, podcast_admin, req, duplicate):
        f = ParserResultFilter(
            req,
            {"parser_result": [Podcast.ParserResult.DUPLICATE]},
            Podcast,
            podcast_admin,
        )
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert duplicate in qs

    @pytest.mark.django_db
    def test_success(self, podcasts, podcast_admin, req, duplicate):
        PodcastFactory(parser_result=Podcast.ParserResult.SUCCESS)
        f = ParserResultFilter(
            req,
            {"parser_result": [Podcast.ParserResult.SUCCESS]},
            Podcast,
            podcast_admin,
        )
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1

    @pytest.mark.django_db
    def test_none(self, podcasts, podcast_admin, req, duplicate):
        f = ParserResultFilter(
            req,
            {"parser_result": ["none"]},
            Podcast,
            podcast_admin,
        )
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3


class TestPodcastTypeFilter:
    @pytest.fixture
    def serial(self):
        return PodcastFactory(podcast_type=Podcast.PodcastType.SERIAL)

    @pytest.mark.django_db
    def test_all(self, podcasts, podcast_admin, req, serial):
        f = PodcastTypeFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    @pytest.mark.django_db
    def test_serial(self, podcasts, podcast_admin, req, serial):
        f = PodcastTypeFilter(
            req,
            {"podcast_type": [Podcast.PodcastType.SERIAL]},
            Podcast,
            podcast_admin,
        )
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert serial in qs

    @pytest.mark.django_db
    def test_episodic(self, podcasts, podcast_admin, req, serial):
        f = PodcastTypeFilter(
            req,
            {"podcast_type": [Podcast.PodcastType.EPISODIC]},
            Podcast,
            podcast_admin,
        )
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert serial not in qs


class TestScheduledFilter:
    @pytest.fixture
    def scheduled(self):
        return PodcastFactory(pub_date=None, parsed=None)

    @pytest.fixture
    def unscheduled(self):
        now = timezone.now()
        return PodcastFactory(
            pub_date=now,
            parsed=now,
            frequency=timezone.timedelta(hours=3),
        )

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


class TestRecommendationAdmin:
    @pytest.mark.django_db
    def test_get_queryset(self, rf):
        RecommendationFactory()
        admin = RecommendationAdmin(Recommendation, AdminSite())
        qs = admin.get_queryset(rf.get("/"))
        assert qs.count() == 1


class TestSubscriptionAdmin:
    @pytest.mark.django_db
    def test_get_queryset(self, rf):
        SubscriptionFactory()
        admin = SubscriptionAdmin(Subscription, AdminSite())
        qs = admin.get_queryset(rf.get("/"))
        assert qs.count() == 1
