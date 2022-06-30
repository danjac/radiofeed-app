import itertools

from datetime import timedelta

from django.db import models
from django.utils import timezone

from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tasks import parse_feed


def schedule_feeds_for_update(limit):
    """Schedules feeds for update in task queue

    Args:
        limit (int): number of podcasts to update
    """

    parse_feed.map(
        itertools.islice(
            get_scheduled_feeds().values_list("pk").distinct(),
            limit,
        )
    )


def get_scheduled_feeds():
    """Returns podcasts scheduled for update.

    Scheduling algorithm:

        1. check once every n hours, where "n" is the number
            of days since the podcast was last updated (i.e. last pub date)
        2. if podcast was last updated within 24 hours, check once an hour.
        3. if podcast was last updated > 24 days, check every 24 hours.
        4. if podcast has not been checked yet (i.e. just added to database), check immediately.

    Only *active* podcasts should be included.

    Examples:

        1. Podcast was last updated 3 days ago, so should be checked every 3 hours
            based on its `parsed` field.
        2. Podcast was last updated 3 hours ago, so should be checked every hour.
        3. Podcast was last updated 30 days ago, should be checked once a day (every 24 hours)
        4. Podcast has just been added e.g. from iTunes API, so should be checked immediately.

    Podcasts are ordered by (in order of priority):

        1. the number of subscribers
        2. promoted podcasts
        3. time since last parsed
        4. time since last published

    The exact timing of when a podcast is checked depends on the number of other podcasts in the queue,
    speed of processing individual feeds, and overall server capacity. This function just returns all
    eligible podcasts ordered by priority.

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
