from datetime import timedelta

from django.db import models
from django.utils import timezone

from radiofeed.podcasts.models import Podcast


def get_scheduled_feeds():
    """Returns podcasts scheduled for update.

    Scheduling algorithm:

        1. check once every n hours, where "n" is the number
            of days since the podcast was last updated
        2. if podcast was last updated within 24 hours, check once an hour.
        3. if podcast was last updated > 24 days, check every 24 hours.
        4. if podcast has not been checked yet, check immediately.

    Example:

        Podcast was last parsed 3 days ago, so should be checked every 3 hours
        based on its `parsed` field.

    Podcasts are ordered by (in order of priority):

        1. the number of subscribers
        2. promoted podcasts
        3. time since last parsed
        4. time since last published

    Returns:
        QuerySet: scheduled podcasts
    """
    now = timezone.now()

    return (
        Podcast.objects.annotate(
            subscribers=models.Count("subscription"),
            days_since_last_pub_date=models.functions.ExtractDay(
                now - models.F("pub_date")
            ),
        )
        .filter(
            models.Q(
                parsed__isnull=True,
            )
            | models.Q(
                pub_date__isnull=True,
            )
            | models.Q(
                days_since_last_pub_date__lt=1,
                parsed__lt=now - timedelta(hours=1),
            )
            | models.Q(
                days_since_last_pub_date__gt=24,
                parsed__lt=now - timedelta(hours=24),
            )
            | models.Q(
                days_since_last_pub_date__range=(1, 24),
                parsed__lt=now
                - timedelta(hours=1) * models.F("days_since_last_pub_date"),
            ),
            active=True,
        )
        .order_by(
            models.F("subscribers").desc(),
            models.F("promoted").desc(),
            models.F("parsed").asc(nulls_first=True),
            models.F("pub_date").desc(nulls_first=True),
        )
    )
