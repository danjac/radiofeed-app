from datetime import timedelta
from unittest import mock

import pytest
from django.contrib.admin.sites import AdminSite
from django.utils import timezone

from radiofeed.factories import create_batch
from radiofeed.podcasts.admin import (
    ActiveFilter,
    CategoryAdmin,
    ImmediateFilter,
    ParserErrorFilter,
    PodcastAdmin,
    PromotedFilter,
    PubDateFilter,
    SubscribedFilter,
    WebsubFilter,
)
from radiofeed.podcasts.factories import create_podcast, create_subscription
from radiofeed.podcasts.models import Category, Podcast


@pytest.fixture(scope="module")
def category_admin():
    return CategoryAdmin(Category, AdminSite())


@pytest.fixture(scope="module")
def podcast_admin():
    return PodcastAdmin(Podcast, AdminSite())


@pytest.fixture
def podcasts():
    return create_batch(create_podcast, 3, active=True, promoted=False)


@pytest.fixture
def req(rf):
    req = rf.get("/")
    req._messages = mock.Mock()
    return req


class TestCategoryAdmin:
    @pytest.mark.django_db
    def test_get_queryset(self, req, category_admin, podcasts, category):
        category.podcasts.set(podcasts)
        qs = category_admin.get_queryset(req)
        assert qs.count() == 1
        assert category_admin.num_podcasts(qs.first()) == 3


class TestPodcastAdmin:
    @pytest.mark.django_db
    def test_get_queryset(self, podcasts, podcast_admin, req):
        qs = podcast_admin.get_queryset(req)
        assert qs.count() == 3

    @pytest.mark.django_db
    def test_get_search_results(self, podcasts, podcast_admin, req):
        podcast = create_podcast(title="Indie Hackers")
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
            "radiofeed.podcasts.admin.scheduler.next_scheduled_update",
            return_value=timezone.now() + timedelta(hours=3),
        )
        assert (
            podcast_admin.next_scheduled_update(podcast) == "2\xa0hours, 59\xa0minutes"
        )


class TestPubDateFilter:
    @pytest.mark.django_db
    def test_none(self, podcasts, podcast_admin, req):
        create_podcast(pub_date=None)
        f = PubDateFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    @pytest.mark.django_db
    def test_no(self, podcasts, podcast_admin, req):
        no_pub_date = create_podcast(pub_date=None)
        f = PubDateFilter(req, {"pub_date": "no"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == no_pub_date

    @pytest.mark.django_db
    def test_yes(self, podcasts, podcast_admin, req):
        no_pub_date = create_podcast(pub_date=None)
        f = PubDateFilter(req, {"pub_date": "yes"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert no_pub_date not in qs


class TestPromotedFilter:
    @pytest.mark.django_db
    def test_none(self, podcasts, podcast_admin, req):
        create_podcast(promoted=False)
        f = PromotedFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    @pytest.mark.django_db
    def test_true(self, podcasts, podcast_admin, req):
        promoted = create_podcast(promoted=True)
        f = PromotedFilter(req, {"promoted": "yes"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == promoted


class TestImmediateFilter:
    @pytest.mark.django_db
    def test_none(self, podcasts, podcast_admin, req):
        create_podcast(immediate=False)
        f = ImmediateFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    @pytest.mark.django_db
    def test_true(self, podcasts, podcast_admin, req):
        immediate = create_podcast(immediate=True)
        f = ImmediateFilter(req, {"immediate": "yes"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == immediate


class TestActiveFilter:
    @pytest.mark.django_db
    def test_none(self, podcasts, podcast_admin, req):
        create_podcast(active=False)
        f = ActiveFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    @pytest.mark.django_db
    def test_active(self, podcasts, podcast_admin, req):
        inactive = create_podcast(active=False)
        f = ActiveFilter(req, {"active": "yes"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert inactive not in qs

    @pytest.mark.django_db
    def test_inactive(self, podcasts, podcast_admin, req):
        inactive = create_podcast(active=False)
        f = ActiveFilter(req, {"active": "no"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert inactive in qs


class TestParserErrorFilter:
    @pytest.fixture
    def duplicate(self):
        return create_podcast(parser_error=Podcast.ParserError.DUPLICATE)

    @pytest.mark.django_db
    def test_all(self, podcasts, podcast_admin, req, duplicate):
        f = ParserErrorFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    @pytest.mark.django_db
    def test_duplicate(self, podcasts, podcast_admin, req, duplicate):
        f = ParserErrorFilter(
            req,
            {"parser_error": Podcast.ParserError.DUPLICATE},
            Podcast,
            podcast_admin,
        )
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert duplicate in qs


class TestSubscribedFilter:
    @pytest.fixture
    def subscribed(self):
        return create_subscription().podcast

    @pytest.mark.django_db
    def test_none(self, podcasts, podcast_admin, req, subscribed):
        f = SubscribedFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    @pytest.mark.django_db
    def test_true(self, podcasts, podcast_admin, req, subscribed):
        f = SubscribedFilter(req, {"subscribed": "yes"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert qs.first() == subscribed


class TestWebsubFilter:
    hub = "https://example.com"

    @pytest.mark.django_db
    def test_none(self, podcasts, podcast_admin, req):
        create_podcast(websub_hub=self.hub)
        f = WebsubFilter(req, {}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 4

    @pytest.mark.django_db
    def test_no(self, podcasts, podcast_admin, req):
        websub = create_podcast(websub_hub=self.hub)
        f = WebsubFilter(req, {"websub": "no"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 3
        assert websub not in qs

    @pytest.mark.django_db
    def test_yes(self, podcasts, podcast_admin, req):
        websub = create_podcast(websub_hub=self.hub)
        f = WebsubFilter(req, {"websub": "yes"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert websub in qs

    @pytest.mark.django_db
    def test_pending(self, podcasts, podcast_admin, req):
        pending = create_podcast(websub_hub=self.hub, websub_mode="")
        f = WebsubFilter(req, {"websub": "pending"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert pending in qs

    @pytest.mark.django_db
    def test_subscribed(self, podcasts, podcast_admin, req):
        subscribed = create_podcast(
            websub_mode="subscribe",
            websub_hub=self.hub,
            websub_expires=timezone.now() + timedelta(days=3),
        )
        f = WebsubFilter(req, {"websub": "subscribed"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert subscribed in qs

    @pytest.mark.django_db
    def test_pending_max_retries(self, podcasts, podcast_admin, req):
        create_podcast(
            websub_mode="",
            websub_hub=self.hub,
            num_websub_retries=3,
        )
        f = WebsubFilter(req, {"websub": "pending"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 0

    @pytest.mark.django_db
    def test_failed_max_retries(self, podcasts, podcast_admin, req):
        create_podcast(
            websub_mode="",
            websub_hub=self.hub,
            num_websub_retries=3,
        )
        f = WebsubFilter(req, {"websub": "failed"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1

    @pytest.mark.django_db
    def test_pending_expired(self, podcasts, podcast_admin, req):
        expired = create_podcast(
            websub_mode="subscribe",
            websub_hub=self.hub,
            websub_expires=timezone.now() - timedelta(days=3),
        )
        f = WebsubFilter(req, {"websub": "pending"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 1
        assert expired in qs

    @pytest.mark.django_db
    def test_subscribed_expired(self, podcasts, podcast_admin, req):
        create_podcast(
            websub_mode="subscribe",
            websub_hub=self.hub,
            websub_expires=timezone.now() - timedelta(days=3),
        )

        f = WebsubFilter(req, {"websub": "subscribed"}, Podcast, podcast_admin)
        qs = f.queryset(req, Podcast.objects.all())
        assert qs.count() == 0
