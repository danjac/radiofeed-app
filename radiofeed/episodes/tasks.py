from __future__ import annotations

from datetime import timedelta

from radiofeed.episodes import emails
from radiofeed.users.models import User


def send_new_episodes_emails(since=timedelta(days=7)):
    """
    Sends new episodes from users' subscribed podcasts

    Runs 06:17 UTC every Wednesday
    """

    send_new_episodes_email.map(
        [
            (user_id, since)
            for user_id in User.objects.filter(
                send_email_notifications=True, is_active=True
            ).values_list("pk", flat=True)
        ]
    )


def send_new_episodes_email(user_id: int, since: timedelta) -> None:
    try:
        emails.send_new_episodes_email(User.objects.get(pk=user_id), since)
    except User.DoesNotExist:
        pass
