from datetime import timedelta

from django import template
from django.utils import timezone
from django.utils.timesince import timesince

from simplecasts import covers
from simplecasts.episodes.models import AudioLog, Episode
from simplecasts.episodes.views import PlayerAction
from simplecasts.request import HttpRequest, RequestContext, is_authenticated_request

register = template.Library()


@register.inclusion_tag("audio_player.html", takes_context=True)
def audio_player(
    context: RequestContext,
    audio_log: AudioLog | None = None,
    action: PlayerAction = "load",
    *,
    hx_oob: bool = False,
) -> dict:
    """Returns audio player."""
    dct = context.flatten() | {
        "action": action,
        "hx_oob": hx_oob,
    }

    match action:
        case "close":
            return dct

        case "play":
            return dct | {"audio_log": audio_log}

        case _:
            return dct | {"audio_log": _get_audio_log(context.request)}


@register.simple_tag(takes_context=True)
def get_media_metadata(context: RequestContext, episode: Episode) -> dict:
    """Returns media session metadata for integration with client device.

    For more details:

        https://developers.google.com/web/updates/2017/02/media-session

    Use with `json_script` template tag to render the JSON in a script tag.
    """

    return {
        "title": episode.cleaned_title,
        "album": episode.podcast.cleaned_title,
        "artist": episode.podcast.cleaned_title,
        "artwork": covers.get_metadata_info(context.request, episode.get_cover_url()),
    }


@register.filter
def format_duration(total_seconds: int, min_value: int = 60) -> str:
    """Formats duration (in seconds) as human readable value e.g. 1 hour, 30 minutes."""
    return (
        timesince(timezone.now() - timedelta(seconds=total_seconds))
        if total_seconds >= min_value
        else ""
    )


def _get_audio_log(request: HttpRequest) -> AudioLog | None:
    if is_authenticated_request(request) and (episode_id := request.player.get()):
        return (
            request.user.audio_logs.select_related(
                "episode",
                "episode__podcast",
            )
            .filter(episode_id=episode_id)
            .first()
        )
    return None
