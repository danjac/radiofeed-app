from __future__ import annotations

from datetime import timedelta

from podtracker.episodes.models import Episode
from podtracker.users.emails import send_user_notification_email
from podtracker.users.models import User


def send_new_episodes_email(user: User, since: timedelta):
    episodes = (
        Episode.objects.recommended(user, since).select_related("podcast").order_by("?")
    )[:6]

    if len(episodes) < 3:
        return

    send_user_notification_email(
        user,
        f"Hi {user.username}, here are some new episodes from your collection.",
        "episodes/emails/new_episodes.txt",
        "episodes/emails/new_episodes.html",
        {
            "episodes": episodes,
        },
    )
