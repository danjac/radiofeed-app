import datetime

from django.contrib.sitemaps import Sitemap
from django.db.models import QuerySet

from .models import Category, Podcast


class CategorySitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.3

    def items(self) -> QuerySet:
        return Category.objects.order_by("name")

    def lastmod(self, item: Category) -> datetime.datetime:
        return item.created


class PodcastSitemap(Sitemap):
    changefreq = "hourly"
    priority = 0.5
    limit = 100

    def items(self) -> QuerySet:
        return Podcast.objects.order_by("-pub_date")

    def lastmod(self, item: Podcast) -> datetime.datetime:
        return item.pub_date
