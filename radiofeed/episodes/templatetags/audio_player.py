from django import template
from django.http import HttpRequest
from django.template.context import RequestContext

from radiofeed.cover_image import get_metadata_info
from radiofeed.episodes.models import AudioLog, Episode

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
        "artwork": get_metadata_info(
            context.request,
            episode.get_cover_url(),
        ),
    }


@register.inclusion_tag("episodes/_audio_player.html", takes_context=True)
def audio_player(context: RequestContext) -> dict:
    """Renders audio player if audio log in current session."""
    dct = {
        "request": context.request,
        "is_playing": False,
    }

    if audio_log := _get_audio_log(context.request):
        dct.update(
            {
                "episode": audio_log.episode,
                "current_time": audio_log.current_time,
                "is_playing": True,
            }
        )
    return dct


@register.inclusion_tag("episodes/_audio_player.html#player", takes_context=True)
def audio_player_update(
    context: RequestContext,
    audio_log: AudioLog | None = None,
    *,
    start_player: bool,
) -> dict:
    """Renders audio player update to open or close the player."""
    dct = {
        "request": context.request,
        "hx_oob": True,
        "is_playing": False,
    }

    if audio_log and start_player:
        dct.update(
            {
                "current_time": audio_log.current_time,
                "episode": audio_log.episode,
                "start_player": True,
                "is_playing": True,
            }
        )
    return dct


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
