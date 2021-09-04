from django import template

from jcasts.episodes.models import AudioLog

register = template.Library()


@register.inclusion_tag("episodes/_play_toggle.html", takes_context=True)
def play_toggle(context, episode, is_detail=False):

    request = context["request"]
    return {
        "episode": episode,
        "user": request.user,
        "is_detail": is_detail,
        "is_playing": request.player.has(episode.id),
    }


@register.inclusion_tag("episodes/_player.html", takes_context=True)
def audio_player(context):
    request = context["request"]

    if request.user.is_authenticated and (episode_id := request.player.get()):

        return {
            "log": AudioLog.objects.filter(user=request.user, episode=episode_id)
            .select_related("episode", "episode__podcast")
            .first()
        }

    return {}
