from django import template
from django.template.context import RequestContext

from radiofeed.episodes.models import Episode
from radiofeed.templatetags import (
    COVER_IMAGE_SIZES,
    get_cover_image_url,
    get_placeholder_cover_url,
)

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
                "src": context.request.build_absolute_uri(
                    get_cover_image_url(episode.podcast.cover_url, size)
                    if episode.podcast.cover_url
                    else get_placeholder_cover_url(size)
                ),
                "sizes": f"{size}x{size}",
                "type": "image/webp",
            }
            for size in COVER_IMAGE_SIZES
        ],
    }


@register.inclusion_tag("episodes/_audio_player.html", takes_context=True)
def audio_player(context: RequestContext) -> dict:
    """Renders audio player if audio log in current session."""

    defaults = {
        "current_time": None,
        "episode": None,
        "is_playing": False,
        "start_player": False,
        "request": context.request,
    }
    if (
        context.request.user.is_authenticated
        and (episode_id := context.request.audio_player.get())
        and (
            audio_log := context.request.user.audio_logs.filter(episode__pk=episode_id)
            .select_related("episode", "episode__podcast")
            .first()
        )
    ):
        return defaults | {
            "episode": audio_log.episode,
            "current_time": audio_log.current_time,
            "is_playing": True,
        }

    return defaults
