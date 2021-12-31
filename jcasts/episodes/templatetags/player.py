from __future__ import annotations

from django import template

from jcasts.episodes.models import AudioLog

register = template.Library()


def get_player_context(log: AudioLog | None):

    return {
        "is_playing": log is not None,
        "episode": log.episode if log else None,
        "log": log,
    }


@register.inclusion_tag("episodes/_player.html", takes_context=True)
def audio_player(context: dict) -> dict:
    request = context["request"]

    if request.user.is_authenticated and (episode_id := request.player.get()):
        return get_player_context(
            AudioLog.objects.filter(user=request.user, episode=episode_id)
            .select_related("episode", "episode__podcast")
            .first()
        )
    return {}
