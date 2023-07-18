from django import template
from django.http import HttpRequest
from django.template.context import RequestContext

from radiofeed.episodes.models import AudioLog, Episode
from radiofeed.template import (
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
        "request": context.request,
        "user": context.request.user,
        "is_playing": False,
        "audio_log": None,
    }

    if audio_log := _get_audio_player_log(context.request):
        return {
            **defaults,
            "audio_log": audio_log,
            "is_playing": True,
        }

    return defaults


def _get_audio_player_log(request: HttpRequest) -> AudioLog | None:
    if request.user.is_authenticated and (episode_id := request.player.get()):
        return (
            request.user.audio_logs.filter(episode__pk=episode_id)
            .select_related("episode", "episode__podcast")
            .first()
        )

    return None
