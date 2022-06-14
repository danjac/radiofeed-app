from __future__ import annotations

from datetime import timedelta

from celery import shared_task

from radiofeed.episodes import emails


@shared_task
def send_new_episodes_email(user_id: int, since: timedelta) -> None:
    emails.send_new_episodes_email(user_id, since)
