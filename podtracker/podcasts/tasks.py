from huey import crontab
from huey.contrib.djhuey import db_task, periodic_task

from podtracker.podcasts import emails, itunes, recommender, scheduler
from podtracker.podcasts.parsers import feed_parser
from podtracker.users.models import User


@db_task()
def recommend() -> None:
    recommender.recommend()


@db_task()
def crawl_itunes() -> None:
    itunes.crawl()


@db_task()
def send_recommendations_email(user_id: int) -> None:
    try:
        emails.send_recommendations_email(User.objects.get(pk=user_id))
    except User.DoesNotExist:
        pass


@db_task()
def send_recommendations_emails() -> None:
    for user_id in User.objects.filter(
        send_email_notifications=True, is_active=True
    ).values_list("pk", flat=True):
        send_recommendations_email(user_id)()


@db_task()
def parse_podcast_feed(podcast_id: int) -> None:
    feed_parser.parse_podcast_feed(podcast_id)


@periodic_task(crontab(minute="*/10"))
def schedule_primary_feeds(**kwargs) -> None:
    for podcast_id in scheduler.schedule_primary_feeds(**kwargs):
        parse_podcast_feed(podcast_id)()


@periodic_task(crontab(hour="*/1", minute="0"))
def schedule_secondary_feeds(**kwargs) -> None:
    for podcast_id in scheduler.schedule_secondary_feeds(**kwargs):
        parse_podcast_feed(podcast_id)()
