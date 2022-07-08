from __future__ import annotations

import datetime

from django.contrib.sitemaps import Sitemap
from django.db.models import QuerySet
from django.utils import timezone

from radiofeed.podcasts.models import Category, Podcast


class CategorySitemap(Sitemap):
    """Category Sitemap."""

    changefreq: str = "never"
    priority: float = 0.3

    def items(self) -> QuerySet[Category]:
        """List all categories."""
        return Category.objects.order_by("name")


class PodcastSitemap(Sitemap):
    """Podcasts Sitemap."""

    changefreq: str = "hourly"
    priority: float = 0.5
    limit: int = 100

    def items(self) -> QuerySet[Podcast]:
        """List all podcasts updated within past 24 hours."""
        return Podcast.objects.filter(
            pub_date__gt=timezone.now() - datetime.timedelta(hours=24),
        ).order_by("-pub_date")

    def lastmod(self, item: Podcast) -> datetime.datetime | None:
        """Returns the last pub date of the podcast."""
        return item.pub_date
