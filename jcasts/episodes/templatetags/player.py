from django import template

from jcasts.episodes.models import AudioLog

register = template.Library()


@register.inclusion_tag("episodes/_player.html", takes_context=True)
def audio_player(context):
    request = context["request"]

    if request.user.is_authenticated:

        return {
            "log": AudioLog.objects.playing(request.user)
            .select_related("episode", "episode__podcast")
            .first()
        }

    return {}
