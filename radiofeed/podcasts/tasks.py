from __future__ import annotations

from celery import shared_task

from radiofeed.podcasts import emails, feed_updater


@shared_task
def feed_update(podcast_id: int) -> None:
    feed_updater.update(podcast_id)


@shared_task
def send_recommendations_email(user_id: int) -> None:
    emails.send_recommendations_email(user_id)
