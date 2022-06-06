from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.utils import timezone

from radiofeed.podcasts.models import Podcast


def schedule_podcasts_for_update() -> models.QuerySet[Podcast]:
    """
    Schedules active podcasts for updates from RSS feed sources.

    Just added (parsed or pub date NULL): check always

    Last pub date < 24 hours: check once an hour
    Last pub date < 1 week: check 8 times a day (every 3 hours)
    Last pub date < 2 weeks: check once a day

    Older: check once a week
    """
    now = timezone.now()

    return (
        Podcast.objects.annotate(subscribers=models.Count("subscription"))
        .filter(
            models.Q(parsed__isnull=True)
            | models.Q(pub_date__isnull=True)
            | models.Q(
                pub_date__lt=now - timedelta(days=14),
                parsed__lt=now - timedelta(hours=24),
            )
            | models.Q(
                pub_date__range=(
                    now - timedelta(days=14),
                    now - timedelta(hours=24),
                ),
                parsed__lt=now - timedelta(hours=3),
            )
            | models.Q(
                pub_date__gt=now - timedelta(hours=24),
                parsed__lt=now - timedelta(hours=1),
            ),
            active=True,
        )
        .order_by(
            models.F("subscribers").desc(),
            models.F("promoted").desc(),
            models.F("parsed").asc(nulls_first=True),
            models.F("pub_date").desc(nulls_first=True),
            models.F("created").desc(),
        )
    )
