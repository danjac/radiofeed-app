import datetime

from django.contrib.sitemaps import Sitemap
from django.db.models import QuerySet
from django.utils import timezone

from radiofeed.episodes.models import Episode


class EpisodeSitemap(Sitemap):
    changefreq = "hourly"
    priority = 0.5
    limit = 100

    def items(self) -> QuerySet:
        return (
            Episode.objects.select_related("podcast")
            .filter(pub_date__gt=timezone.now() - datetime.timedelta(hours=24))
            .order_by("-pub_date")
        )

    def lastmod(self, item) -> datetime.datetime:
        return item.pub_date
