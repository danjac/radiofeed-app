import datetime

from django.contrib.sitemaps import Sitemap
from django.utils import timezone

from radiofeed.podcasts.models import Category, Podcast


class CategorySitemap(Sitemap):
    """Category Sitemap."""

    changefreq = "never"
    priority = 0.3

    def items(self):
        """List all categories.

        Returns:
            QuerySet
        """
        return Category.objects.order_by("name")


class PodcastSitemap(Sitemap):
    """Podcasts Sitemap."""

    changefreq = "hourly"
    priority = 0.5
    limit = 100

    def items(self):
        """List all podcasts updated within past 24 hours.

        Returns:
            QuerySet
        """
        return Podcast.objects.filter(
            pub_date__gt=timezone.now() - datetime.timedelta(hours=24),
        ).order_by("-pub_date")

    def lastmod(self, item):
        """Returns the last pub date of the podcast.

        Returns:
            datetime
        """
        return item.pub_date
