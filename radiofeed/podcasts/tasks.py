from __future__ import annotations

from huey.contrib.djhuey import db_task

from radiofeed.podcasts import emails, feed_updater
from radiofeed.podcasts.models import Podcast
from radiofeed.users.models import User


@db_task()
def feed_update(podcast_id: int) -> None:
    feed_updater.FeedUpdater(Podcast.objects.get(pk=podcast_id)).update()


@db_task()
def recommendations_email(user_id: int) -> None:
    emails.recommendations(User.objects.email_notification_recipients().get(pk=user_id))
