import datetime

from django.contrib.sitemaps import Sitemap
from django.db.models import QuerySet

from .models import Episode


class EpisodeSitemap(Sitemap):
    changefreq = "hourly"
    priority = 0.5
    limit = 100

    def items(self) -> QuerySet:
        return Episode.objects.select_related("podcast").order_by("-pub_date")

    def lastmod(self, item: Episode) -> datetime.datetime:
        return item.pub_date
