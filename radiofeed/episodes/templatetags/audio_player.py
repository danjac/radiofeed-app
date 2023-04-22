from __future__ import annotations

from django import template
from django.template.context import RequestContext

register = template.Library()


@register.inclusion_tag("episodes/audio_player.html", takes_context=True)
def audio_player(context: RequestContext) -> dict:
    """Returns details of current episode in player."""
    if episode_id := context.request.player.get():
        if (
            audio_log := context.request.user.audio_logs.filter(episode__pk=episode_id)
            .select_related("episode", "episode__podcast")
            .first()
        ):
            return {
                "request": context.request,
                "episode": audio_log.episode,
                "current_time": audio_log.current_time,
                "is_playing": True,
            }

    return {}
