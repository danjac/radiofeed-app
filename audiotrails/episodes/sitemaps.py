import datetime

from django.contrib.sitemaps import Sitemap
from django.db.models import QuerySet
from django.utils import timezone

from .models import Episode


class EpisodeSitemap(Sitemap):
    changefreq: str = "hourly"
    priority: float = 0.5
    limit: int = 100

    def items(self) -> QuerySet:
        return (
            Episode.objects.select_related("podcast")
            .filter(pub_date__gt=timezone.now() - datetime.timedelta(hours=24))
            .order_by("-pub_date")
        )

    def lastmod(self, item: Episode) -> datetime.datetime:
        return item.pub_date
