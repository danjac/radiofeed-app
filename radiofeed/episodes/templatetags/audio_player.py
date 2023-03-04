from __future__ import annotations

from django import template
from django.template.context import RequestContext

register = template.Library()


@register.inclusion_tag("episodes/includes/audio_player.html", takes_context=True)
def audio_player(context: RequestContext) -> dict:
    """Returns details of current episode in player."""
    if (
        log := context.request.user.audio_logs.filter(is_playing=True)
        .select_related("episode", "episode__podcast")
        .first()
    ):
        return {
            "request": context.request,
            "episode": log.episode,
            "current_time": log.current_time,
            "is_playing": True,
        }

    return {}
