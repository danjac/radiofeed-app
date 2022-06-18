from __future__ import annotations

from huey.contrib.djhuey import db_task

from radiofeed.podcasts import emails, feed_updater, itunes
from radiofeed.podcasts.models import Podcast
from radiofeed.users.models import User


@db_task(priority=3)
def feed_update(podcast_id: int) -> None:
    feed_updater.FeedUpdater(Podcast.objects.get(pk=podcast_id)).update()


@db_task(priority=6)
def send_recommendations_email(user_id: int) -> None:
    emails.send_recommendations_email(
        User.objects.email_notification_recipients().get(pk=user_id)
    )


@db_task(priority=1)
def parse_itunes_feed(itunes_podcast_id: str) -> None:
    itunes.parse_feed(itunes_podcast_id)
