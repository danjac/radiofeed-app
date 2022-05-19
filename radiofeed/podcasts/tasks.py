from __future__ import annotations

import logging

from huey import crontab
from huey.contrib.djhuey import db_periodic_task, db_task

from radiofeed.podcasts import emails, recommender, scheduler
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
    for user_id in User.objects.filter(
        send_email_notifications=True, is_active=True
    ).values_list("pk", flat=True):
        send_recommendations_email(user_id)()


@db_periodic_task(crontab(minute="*/6"))
def schedule_primary_feeds() -> None:
    """Schedules primary podcast feeds for update

    Runs every 6 minutes
    """

    for podcast_id in scheduler.get_primary_podcasts().values_list("pk", flat=True)[
        :300
    ]:
        parse_podcast_feed(podcast_id)()


@db_periodic_task(crontab(minute="*/12"))
def schedule_frequent_feeds() -> None:
    """Schedules podcast feeds for update

    Runs every 12 minutes
    """

    for podcast_id in scheduler.get_frequent_podcasts().values_list("pk", flat=True)[
        :300
    ]:
        parse_podcast_feed(podcast_id)()


@db_periodic_task(crontab(minute="15,45"))
def schedule_sporadic_feeds() -> None:
    """Schedules podcast feeds for update

    Runs every 15 and 45 minutes past the hour
    """

    for podcast_id in scheduler.get_sporadic_podcasts().values_list("pk", flat=True)[
        :300
    ]:
        parse_podcast_feed(podcast_id)()


@db_task()
def parse_podcast_feed(podcast_id: int) -> None:
    feed_parser.parse_podcast_feed(podcast_id)


@db_task()
def send_recommendations_email(user_id: int) -> None:
    try:
        emails.send_recommendations_email(User.objects.get(pk=user_id))
    except User.DoesNotExist:
        pass
