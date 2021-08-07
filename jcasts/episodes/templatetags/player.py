from __future__ import annotations

from django import template

from jcasts.episodes.views.player import get_player_audio_log

register = template.Library()


@register.inclusion_tag("episodes/_player.html", takes_context=True)
def render_player(context: dict) -> dict:
    return {"log": get_player_audio_log(context["request"])}
