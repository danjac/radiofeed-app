from __future__ import annotations

from datetime import timedelta

from huey import crontab
from huey.contrib.djhuey import db_periodic_task, db_task

from radiofeed.episodes import emails
from radiofeed.users.models import User


@db_periodic_task(crontab(hour=6, minute=17, day_of_week=3))
def send_new_episodes_emails():
    """
    Sends new episodes from users' subscribed podcasts

    Runs 6:17 UTC every Wednesday
    """
    since = timedelta(days=7)
    for user in User.objects.filter(send_email_notifications=True, is_active=True):
        send_new_episodes_email(user.id, since)()


@db_task()
def send_new_episodes_email(user_id: int, since: timedelta) -> None:
    try:
        emails.send_new_episodes_email(User.objects.get(pk=user_id), since)
    except User.DoesNotExist:
        pass
