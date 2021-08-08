from __future__ import annotations

from django import template

from jcasts.episodes.models import AudioLog

register = template.Library()


@register.inclusion_tag("episodes/_player.html", takes_context=True)
def render_player(context: dict) -> dict:
    if context["request"].user.is_anonymous:
        return {}

    log = (
        AudioLog.objects.filter(user=context["request"].user, is_playing=True)
        .select_related("episode", "episode__podcast")
        .first()
    )

    return {"log": log}
