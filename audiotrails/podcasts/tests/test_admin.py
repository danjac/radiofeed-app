from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase

from audiotrails.podcasts.admin import (
    ActiveFilter,
    PodcastAdmin,
    PromotedFilter,
    PubDateFilter,
)
from audiotrails.podcasts.factories import PodcastFactory
from audiotrails.podcasts.models import Podcast


class PodcastAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.podcasts = PodcastFactory.create_batch(3, active=True, promoted=False)

    def setUp(self) -> None:
        self.rf = RequestFactory()
        self.admin = PodcastAdmin(Podcast, AdminSite())
        self.request = self.rf.get("/")

    def test_source(self) -> None:
        podcast = self.podcasts[0]
        self.assertEqual(self.admin.source(podcast), podcast.get_domain())

    def test_get_search_results(self) -> None:
        podcast = PodcastFactory(title="Indie Hackers")
        qs, _ = self.admin.get_search_results(
            self.request, Podcast.objects.all(), "Indie Hackers"
        )
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), podcast)

    def test_get_search_results_no_search_term(self) -> None:
        qs, _ = self.admin.get_search_results(self.request, Podcast.objects.all(), "")
        self.assertEqual(qs.count(), 3)

    def test_pub_date_filter_none(self) -> None:
        PodcastFactory(pub_date=None)
        f = PubDateFilter(self.request, {}, Podcast, self.admin)
        qs = f.queryset(self.request, Podcast.objects.all())
        self.assertEqual(qs.count(), 4)

    def test_pub_date_filter_false(self) -> None:
        no_pub_date = PodcastFactory(pub_date=None)
        f = PubDateFilter(self.request, {"pub_date": "no"}, Podcast, self.admin)
        qs = f.queryset(self.request, Podcast.objects.all())
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), no_pub_date)

    def test_pub_date_filter_true(self) -> None:
        no_pub_date = PodcastFactory(pub_date=None)
        f = PubDateFilter(self.request, {"pub_date": "yes"}, Podcast, self.admin)
        qs = f.queryset(self.request, Podcast.objects.all())
        self.assertEqual(qs.count(), 3)
        self.assertNotIn(no_pub_date, qs)

    def test_active_filter_none(self) -> None:
        PodcastFactory(active=False)
        f = ActiveFilter(self.request, {}, Podcast, self.admin)
        qs = f.queryset(self.request, Podcast.objects.all())
        self.assertEqual(qs.count(), 4)

    def test_active_filter_false(self) -> None:
        inactive = PodcastFactory(active=False)
        f = ActiveFilter(self.request, {"active": "no"}, Podcast, self.admin)
        qs = f.queryset(self.request, Podcast.objects.all())
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), inactive)

    def test_active_filter_true(self) -> None:
        inactive = PodcastFactory(active=False)
        f = ActiveFilter(self.request, {"active": "yes"}, Podcast, self.admin)
        qs = f.queryset(self.request, Podcast.objects.all())
        self.assertEqual(qs.count(), 3)
        self.assertNotIn(inactive, qs)

    def test_promoted_filter_none(self) -> None:
        PodcastFactory(promoted=False)
        f = PromotedFilter(self.request, {}, Podcast, self.admin)
        qs = f.queryset(self.request, Podcast.objects.all())
        self.assertEqual(qs.count(), 4)

    def test_promoted_filter_true(self) -> None:
        promoted = PodcastFactory(promoted=True)
        f = PromotedFilter(self.request, {"promoted": "yes"}, Podcast, self.admin)
        qs = f.queryset(self.request, Podcast.objects.all())
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), promoted)
