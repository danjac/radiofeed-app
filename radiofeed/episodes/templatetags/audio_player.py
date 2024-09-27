from typing import Literal

from django import template
from django.http import HttpRequest
from django.template.context import RequestContext
from django.templatetags.static import static
from django.utils.html import format_html

from radiofeed.cover_image import get_metadata_info
from radiofeed.episodes.models import AudioLog, Episode

register = template.Library()


@register.inclusion_tag("episodes/_audio_player.html", takes_context=True)
def audio_player(context: RequestContext) -> dict:
    """Renders audio player if audio log in current session."""
    return {
        "request": context.request,
        "audio_log": _get_audio_log(context.request),
    }


@register.inclusion_tag("episodes/_audio_player.html", takes_context=True)
def audio_player_update(
    context: RequestContext,
    action: Literal["open", "close"],
    audio_log: AudioLog | None = None,
) -> dict:
    """Renders audio player update to open or close the player."""
    dct = {
        "request": context.request,
        "hx_oob": True,
    }

    if audio_log is not None and action == "open":
        dct.update(
            {
                "audio_log": audio_log,
                "start_player": True,
            }
        )
    return dct


@register.simple_tag(takes_context=True)
def audio_player_script(context: RequestContext) -> str:
    """Renders the JS required for audio player."""
    if context.request.user.is_authenticated:
        return format_html('<script src="{}"></script>', static("audio-player.js"))
    return ""


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
        "artwork": get_metadata_info(context.request, episode.get_cover_url()),
    }


def _get_audio_log(request: HttpRequest) -> AudioLog | None:
    if request.user.is_authenticated and (episode_id := request.player.get()):
        return (
            request.user.audio_logs.filter(episode__pk=episode_id)
            .select_related(
                "episode",
                "episode__podcast",
            )
            .first()
        )
    return None
