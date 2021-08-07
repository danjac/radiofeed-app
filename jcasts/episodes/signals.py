from typing import Any

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.http import HttpRequest

from jcasts.episodes.models import AudioLog
from jcasts.shared.typedefs import AnyUser, AuthenticatedUser


@receiver(user_logged_in)
def open_player(
    sender: Any, user: AuthenticatedUser, request: HttpRequest, **kwargs
) -> None:

    if (
        log := AudioLog.objects.filter(
            user=user,
            completed__isnull=True,
            autoplay=True,
        )
        .select_related("episode")
        .order_by("-updated")
        .first()
    ) :
        request.player.add_episode(log.episode)


@receiver(user_logged_out)
def close_player(sender: Any, user: AnyUser, request: HttpRequest, **kwargs) -> None:

    # removes current player from session
    request.session.pop("player", None)
