import datetime

from typing import ClassVar

from django.contrib.sitemaps import Sitemap
from django.db.models import QuerySet
from django.utils import timezone

from jcasts.podcasts.models import Category, Podcast


class CategorySitemap(Sitemap):
    changefreq: ClassVar[str] = "never"
    priority: ClassVar[float] = 0.3

    def items(self) -> QuerySet:
        return Category.objects.order_by("name")


class PodcastSitemap(Sitemap):
    changefreq: ClassVar[str] = "hourly"
    priority: ClassVar[float] = 0.5
    limit: ClassVar[int] = 100

    def items(self) -> QuerySet:
        return Podcast.objects.filter(
            pub_date__isnull=False,
            pub_date__gt=timezone.now() - datetime.timedelta(hours=24),
        ).order_by("-pub_date")

    def lastmod(self, item: Podcast) -> datetime.datetime:
        return item.pub_date
