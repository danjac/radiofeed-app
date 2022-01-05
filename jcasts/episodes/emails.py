from __future__ import annotations

from datetime import timedelta

from django_rq import job

from jcasts.episodes.models import Episode
from jcasts.shared.typedefs import User
from jcasts.users.emails import send_user_notification_email


@job("mail")
def send_new_episodes_email(user: User, since: timedelta) -> None:
    """Sends email with new episodes added to user's collection."""

    episodes = (
        Episode.objects.recommended(user, since).select_related("podcast").order_by("?")
    )[:3]

    if episodes.count() not in (2, 3):
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
