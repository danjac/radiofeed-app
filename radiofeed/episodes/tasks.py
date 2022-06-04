from __future__ import annotations

from datetime import timedelta

from celery import shared_task

from radiofeed.episodes import emails
from radiofeed.users.models import User


@shared_task
def send_new_episodes_emails(since=timedelta(days=7)):
    for user_id in User.objects.filter(
        send_email_notifications=True, is_active=True
    ).values_list("pk", flat=True):

        send_new_episodes_email.delay(user_id, since)


@shared_task
def send_new_episodes_email(user_id: int, since: timedelta) -> None:
    try:
        emails.send_new_episodes_email(User.objects.get(pk=user_id), since)
    except User.DoesNotExist:
        pass
