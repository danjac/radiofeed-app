from typing import Literal, TypedDict

from django import template
from django.http import HttpRequest
from django.template.context import RequestContext
from django.templatetags.static import static
from django.utils.html import format_html

from radiofeed.cover_image import get_metadata_info
from radiofeed.episodes.models import AudioLog, Episode

register = template.Library()

AudioPlayerAction = Literal["play", "close"]


class PlayerInfo(TypedDict):
    """Audio player context."""

    request: HttpRequest
    audio_log: AudioLog | None
    start_player: bool
    hx_oob: bool


@register.inclusion_tag("episodes/_audio_player.html", takes_context=True)
def audio_player(context: RequestContext) -> PlayerInfo:
    """Renders audio player if audio log in current session."""

    dct = PlayerInfo(
        request=context.request,
        audio_log=None,
        hx_oob=False,
        start_player=False,
    )

    if context.request.user.is_authenticated and (
        episode_id := context.request.player.get()
    ):
        dct["audio_log"] = (
            context.request.user.audio_logs.filter(episode__pk=episode_id)
            .select_related(
                "episode",
                "episode__podcast",
            )
            .first()
        )

    return dct


@register.inclusion_tag("episodes/_audio_player.html", takes_context=True)
def audio_player_update(
    context: RequestContext,
    action: AudioPlayerAction,
    audio_log: AudioLog | None = None,
) -> PlayerInfo:
    """Renders audio player update to open or close the player."""

    dct = PlayerInfo(
        request=context.request,
        audio_log=None,
        hx_oob=True,
        start_player=False,
    )

    if action == "play" and audio_log is not None:
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
