from __future__ import annotations

from typing import cast

from django import template

from radiofeed.common.http import HttpRequest
from radiofeed.episodes.models import AudioLog

register = template.Library()


@register.inclusion_tag("episodes/player.html", takes_context=True)
def audio_player(context: dict) -> dict:
    """Returns details of current episode in player."""
    request = cast(HttpRequest, context["request"])

    if (
        request.user.is_authenticated
        and (episode_id := request.player.get())
        and (
            log := AudioLog.objects.filter(user=request.user, episode=episode_id)
            .select_related("episode", "episode__podcast")
            .first()
        )
    ):
        return {
            "request": request,
            "episode": log.episode,
            "current_time": log.current_time,
            "is_playing": True,
        }
    return {}
