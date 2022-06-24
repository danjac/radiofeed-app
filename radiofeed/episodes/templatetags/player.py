from django import template

from radiofeed.episodes.models import AudioLog

register = template.Library()


@register.inclusion_tag("episodes/player.html", takes_context=True)
def audio_player(context):
    request = context["request"]

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
