from datetime import timedelta

from huey import crontab
from huey.contrib.djhuey import db_periodic_task, db_task

from podtracker.podcasts import emails, itunes, recommender, scheduler
from podtracker.podcasts.parsers import feed_parser
from podtracker.users.models import User


@db_periodic_task(crontab(hour=3, minute=20))
def recommend() -> None:
    recommender.recommend()


@db_periodic_task(crontab(hour=5, minute=12))
def crawl_itunes() -> None:
    itunes.crawl()


@db_periodic_task(crontab(hour=9, minute=12, day_of_week=1))
def send_recommendations_emails() -> None:
    for user_id in User.objects.filter(
        send_email_notifications=True, is_active=True
    ).values_list("pk", flat=True):
        send_recommendations_email(user_id)()


@db_periodic_task(crontab(minute="*/12"))
def schedule_primary_feeds() -> None:
    for podcast_id in scheduler.schedule_primary_feeds(limit=300):
        parse_podcast_feed(podcast_id)()


@db_periodic_task(crontab(minute="*/6"))
def schedule_frequent_feeds() -> None:
    for podcast_id in scheduler.schedule_secondary_feeds(
        after=timedelta(hours=336), before=timedelta(hours=3), limit=300
    ):
        parse_podcast_feed(podcast_id)()


@db_periodic_task(crontab(minute="15,45"))
def schedule_sporadic_feeds() -> None:
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
