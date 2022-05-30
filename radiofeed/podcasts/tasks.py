from __future__ import annotations

import logging

from datetime import timedelta

from django.db.models import Exists, F, OuterRef, Q, QuerySet
from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import db_periodic_task, db_task

from radiofeed.podcasts import emails, recommender
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.parsers import feed_parser
from radiofeed.users.models import User

logger = logging.getLogger(__name__)


@db_periodic_task(crontab(hour=3, minute=20))
def recommend() -> None:
    """
    Generates podcast recommendations

    Runs 03:20 UTC every day
    """
    recommender.recommend()


@db_periodic_task(crontab(hour=9, minute=12, day_of_week=1))
def send_recommendations_emails() -> None:
    """
    Sends recommended podcasts to users

    Runs at 09:12 UTC every Monday
    """
    send_recommendations_email.map(
        User.objects.filter(
            send_email_notifications=True,
            is_active=True,
        ).values_list("pk")
    )


@db_periodic_task(crontab(minute="*/6"))
def schedule_recent_feeds():
    """Schedules podcast feeds for update.

    Runs every 6 minutes
    """

    schedule_podcast_feeds(
        Podcast.objects.filter(
            pub_date__gte=timezone.now() - timedelta(days=14),
        )
    )


@db_periodic_task(crontab(minute="15,45"))
def schedule_sporadic_feeds():
    """Schedules sporadic podcast feeds for update.

    Runs every 15 and 45 minutes past the hour
    """

    schedule_podcast_feeds(
        Podcast.objects.filter(
            pub_date__lt=timezone.now() - timedelta(days=14),
        )
    )


def schedule_podcast_feeds(podcasts: QuerySet[Podcast], limit: int = 360) -> None:
    parse_podcast_feed.map(
        podcasts.with_subscribed()
        .filter(active=True)
        .order_by(
            F("subscribed").desc(),
            F("promoted").desc(),
            F("parsed").asc(nulls_first=True),
            F("pub_date").desc(nulls_first=True),
            F("created").desc(),
        )
        .values_list("pk")
        .distinct()[:limit]
    )


@db_task()
def parse_podcast_feed(podcast_id: int) -> None:
    feed_parser.parse_podcast_feed(podcast_id)


@db_task()
def send_recommendations_email(user_id: int) -> None:
    try:
        emails.send_recommendations_email(User.objects.get(pk=user_id))
    except User.DoesNotExist:
        pass
