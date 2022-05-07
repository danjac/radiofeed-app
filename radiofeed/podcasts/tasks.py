from __future__ import annotations

import logging

from datetime import timedelta

from huey import crontab
from huey.contrib.djhuey import db_periodic_task, db_task

from radiofeed.podcasts import emails, itunes, recommender, scheduler
from radiofeed.podcasts.parsers import feed_parser
from radiofeed.users.models import User

logger = logging.getLogger(__name__)


@db_periodic_task(crontab(hour=3, minute=20))
def recommend() -> None:
    """
    Generates podcast recommendations

    Runs 3:20 UTC every day
    """
    recommender.recommend()


@db_periodic_task(crontab(hour=5, minute=12))
def crawl_itunes() -> None:
    """
    Crawls iTunes site for new podcasts

    Runs at 5:12 UTC every day
    """
    for feed in itunes.crawl():
        logger.debug(feed.title)


@db_periodic_task(crontab(hour=9, minute=12, day_of_week=1))
def send_recommendations_emails() -> None:
    """
    Sends recommended podcasts to users

    Runs at 9:12 UTC every Monday
    """
    for user_id in User.objects.filter(
        send_email_notifications=True, is_active=True
    ).values_list("pk", flat=True):
        send_recommendations_email(user_id)()


@db_periodic_task(crontab(minute="*/12"))
def schedule_primary_feeds() -> None:
    """
    Schedule all subscribed or promoted feeds

    Runs every 12 minutes
    """
    for podcast_id in scheduler.schedule_primary_feeds(limit=300):
        parse_podcast_feed(podcast_id)()


@db_periodic_task(crontab(minute="*/6"))
def schedule_frequent_feeds() -> None:
    """
    Schedule podcast feeds newer than 2 weeks

    Runs every 6 minutes
    """
    for podcast_id in scheduler.schedule_secondary_feeds(
        after=timedelta(hours=336), before=timedelta(hours=3), limit=300
    ):
        parse_podcast_feed(podcast_id)()


@db_periodic_task(crontab(minute="15,45"))
def schedule_sporadic_feeds() -> None:
    """
    Schedule podcast feeds older than 2 weeks

    Runs at 15 and 45 minutes past the hour
    """
    for podcast_id in scheduler.schedule_secondary_feeds(
        before=timedelta(hours=336), limit=300
    ):
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
