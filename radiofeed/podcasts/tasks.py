from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import db_periodic_task, db_task

from radiofeed.podcasts import emails, recommender
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.parsers import feed_parser
from radiofeed.users.models import User


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
def parse_frequent_feeds() -> None:
    """Parse frequent feeds (last pub date < 14 days).

    Runs every 6 minutes.
    """
    now = timezone.now()

    parse_podcast_feeds(
        Podcast.objects.filter(
            models.Q(pub_date__isnull=True)
            | models.Q(parsed__isnull=True)
            | models.Q(
                pub_date__range=(now - timedelta(days=14), now - timedelta(hours=24)),
                parsed__lt=now - timedelta(hours=3),
            )
            | models.Q(
                pub_date__gt=now - timedelta(hours=24),
                parsed__lt=now - timedelta(hours=1),
            ),
        )
    )


@db_periodic_task(crontab(minute="15,15"))
def parse_sporadic_feeds() -> None:
    """Parse sporadic feeds (last pub date > 14 days).

    Runs every 15 and 45 minutes past the hour.
    """
    now = timezone.now()

    parse_podcast_feeds(
        Podcast.objects.filter(
            pub_date__lt=now - timedelta(days=14),
            parsed__lt=now - timedelta(hours=24),
        ),
    )


def parse_podcast_feeds(podcasts: models.QuerySet[Podcast], limit: int = 300) -> None:

    parse_podcast_feed.map(
        podcasts.annotate(subscribers=models.Count("subscription"))
        .filter(active=True)
        .order_by(
            models.F("subscribers").desc(),
            models.F("promoted").desc(),
            models.F("parsed").asc(nulls_first=True),
            models.F("pub_date").desc(nulls_first=True),
            models.F("created").desc(),
        )
        .values_list("pk")
        .distinct()[:limit]
    )


@db_task()
def parse_podcast_feed(podcast_id: int) -> None:
    feed_parser.parse_podcast_feed(Podcast.objects.get(pk=podcast_id))


@db_task()
def send_recommendations_email(user_id: int) -> None:
    emails.send_recommendations_email(User.objects.get(pk=user_id))
