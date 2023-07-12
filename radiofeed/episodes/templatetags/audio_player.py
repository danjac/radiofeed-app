from django import template
from django.template.context import RequestContext
from django.templatetags.static import static

from radiofeed.episodes.models import Episode
from radiofeed.template import cover_image_url

register = template.Library()


@register.simple_tag(takes_context=True)
def get_media_metadata(context: RequestContext, episode: Episode) -> dict:
    """Returns media session metadata for integration with client device.

    For more details:

        https://developers.google.com/web/updates/2017/02/media-session
    """

    return {
        "title": episode.cleaned_title,
        "album": episode.podcast.cleaned_title,
        "artist": episode.podcast.owner,
        "artwork": [
            {
                "src": (
                    context.request.build_absolute_uri(
                        cover_image_url(episode.podcast.cover_url, size=size)
                    )
                    if episode.podcast.cover_url
                    else static(f"img/placeholder-{size}.webp")
                ),
                "sizes": f"{size}x{size}",
                "type": "image/webp",
            }
            for size in [100, 200, 300]
        ],
    }


@register.inclusion_tag("episodes/_audio_player.html", takes_context=True)
def audio_player(context: RequestContext) -> dict:
    """Returns details of current episode in player."""
    if (episode_id := context.request.player.get()) and (
        audio_log := context.request.user.audio_logs.filter(episode__pk=episode_id)
        .select_related("episode", "episode__podcast")
        .first()
    ):
        return {
            "audio_log": audio_log,
            "is_playing": True,
            "request": context.request,
        }

    return {}
