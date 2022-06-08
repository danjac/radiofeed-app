from __future__ import annotations

from datetime import timedelta

from huey.contrib.djhuey import db_task

from radiofeed.episodes import emails
from radiofeed.users.models import User


@db_task()
def send_new_episodes_email(user_id: int, since: timedelta) -> None:
    emails.send_new_episodes_email(User.objects.get(pk=user_id), since)
