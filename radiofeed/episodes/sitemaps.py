from __future__ import annotations

import datetime

from django.contrib.sitemaps import Sitemap
from django.db.models import QuerySet
from django.utils import timezone

from radiofeed.episodes.models import Episode


class EpisodeSitemap(Sitemap):
    """Sitemap of recent episodes."""

    changefreq = "hourly"
    priority = 0.5
    limit = 100

    def items(self) -> QuerySet[Episode]:
        """Returns new episodes published within last 24 hours."""
        return (
            Episode.objects.select_related("podcast")
            .filter(pub_date__gt=timezone.now() - datetime.timedelta(hours=24))
            .order_by("-pub_date")
        )

    def lastmod(self, item: Episode) -> datetime.datetime:
        """Returns episode pub date."""
        return item.pub_date
