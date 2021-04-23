from django import template

from ..models import AudioLog

register = template.Library()


@register.simple_tag(takes_context=True)
def is_playing(context, episode):
    return context["request"].session.get("player_episode") == episode.id


@register.simple_tag(takes_context=True)
def get_player(context):
    request = context["request"]
    if request.user.is_anonymous or "player_episode" not in request.session:
        return {}
    if (
        log := (
            AudioLog.objects.filter(
                user=request.user, episode=request.session["player_episode"]
            )
            .select_related("episode", "episode__podcast")
            .first()
        )
    ) is None:
        return {}

    return {
        "episode": log.episode,
        "current_time": log.current_time,
    }
