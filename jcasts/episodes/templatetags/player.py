from __future__ import annotations

from django import template

from jcasts.episodes.models import AudioLog

register = template.Library()


@register.inclusion_tag("episodes/_player.html", takes_context=True)
def audio_player(context: dict) -> dict:
    request = context["request"]

    if request.user.is_authenticated and (episode_id := request.player.get()):

        return {
            "log": AudioLog.objects.filter(user=request.user, episode=episode_id)
            .select_related("episode", "episode__podcast")
            .first()
        }

    return {}
