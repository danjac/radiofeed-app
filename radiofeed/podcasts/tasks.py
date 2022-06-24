from huey.contrib.djhuey import db_task

from radiofeed.podcasts import emails, feed_updater
from radiofeed.podcasts.models import Podcast
from radiofeed.users.models import User


@db_task()
def feed_update(podcast_id):
    feed_updater.FeedUpdater(Podcast.objects.get(pk=podcast_id)).update()


@db_task()
def send_recommendations_email(user_id):
    emails.send_recommendations_email(
        User.objects.email_notification_recipients().get(pk=user_id)
    )
