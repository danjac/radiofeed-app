from __future__ import annotations

from celery import shared_task

from radiofeed.podcasts import emails, recommender, scheduler
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.parsers import feed_parser
from radiofeed.users.models import User


@shared_task
def recommend() -> None:
    recommender.recommend()


@shared_task
def send_recommendations_emails() -> None:
    for user_id in User.objects.filter(
        send_email_notifications=True,
        is_active=True,
    ).values_list("pk", flat=True):
        send_recommendations_email.delay(user_id)


@shared_task
def schedule_podcast_feeds(limit: int = 300) -> None:
    for podcast_id in (
        scheduler.schedule_podcasts_for_update()
        .values_list("pk", flat=True)
        .distinct()[:limit]
    ):
        parse_podcast_feed.delay(podcast_id)


@shared_task
def parse_podcast_feed(podcast_id: int) -> None:
    try:
        feed_parser.parse_podcast_feed(Podcast.objects.get(pk=podcast_id))
    except Podcast.DoesNotExist:
        pass


@shared_task
def send_recommendations_email(user_id: int) -> None:
    try:
        emails.send_recommendations_email(User.objects.get(pk=user_id))
    except User.DoesNotExist:
        pass
