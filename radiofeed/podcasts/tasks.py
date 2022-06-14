from __future__ import annotations

from celery import shared_task

from radiofeed.podcasts import emails, feed_updater
from radiofeed.podcasts.models import Podcast
from radiofeed.users.models import User


@shared_task
def feed_update(podcast_id: int) -> None:
    feed_updater.FeedUpdater(Podcast.objects.get(pk=podcast_id)).update()


@shared_task
def send_recommendations_email(user_id: int) -> None:
    emails.send_recommendations_email(
        User.objects.email_notification_recipients().get(pk=user_id)
    )
