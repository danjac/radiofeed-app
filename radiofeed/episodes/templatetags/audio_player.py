from __future__ import annotations

from django import template
from django.template.context import RequestContext

from radiofeed.episodes.models import AudioLog

register = template.Library()


@register.inclusion_tag("episodes/audio_player.html", takes_context=True)
def audio_player(context: RequestContext) -> dict:
    """Returns details of current episode in player."""
    if (
        context.request.user.is_authenticated
        and (episode_id := context.request.player.get())
        and (
            log := AudioLog.objects.filter(
                user=context.request.user, episode=episode_id
            )
            .select_related("episode", "episode__podcast")
            .first()
        )
    ):
        return {
            "request": context.request,
            "episode": log.episode,
            "current_time": log.current_time,
            "is_playing": True,
        }
    return {}
