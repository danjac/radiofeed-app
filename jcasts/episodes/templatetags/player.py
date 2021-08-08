from __future__ import annotations

from django import template

from jcasts.episodes.models import AudioLog

register = template.Library()


@register.inclusion_tag("episodes/_player.html", takes_context=True)
def render_player(context: dict) -> dict:
    return {
        "log": (
            AudioLog.objects.playing(context["request"].user)
            .select_related("episode", "episode__podcast")
            .first()
        )
    }
