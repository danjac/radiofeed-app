from typing import Literal

from django import template
from django.http import HttpRequest
from django.template.context import RequestContext

from radiofeed import cover_image
from radiofeed.episodes.models import AudioLog, Episode

register = template.Library()

Action = Literal["load", "play", "close"]


@register.inclusion_tag("episodes/audio_player.html", takes_context=True)
def audio_player(
    context: RequestContext,
    audio_log: AudioLog | None = None,
    action: Action = "load",
    *,
    hx_oob: bool = False,
) -> dict:
    """Returns audio player."""

    dct = {
        "request": context.request,
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
        "artwork": cover_image.get_metadata_info(
            context.request,
            episode.get_cover_url(),
        ),
    }


def _get_audio_log(request: HttpRequest) -> AudioLog | None:
    if request.user.is_authenticated and (episode_id := request.player.get()):
        return (
            request.user.audio_logs.select_related(
                "episode",
                "episode__podcast",
            )
            .filter(episode_id=episode_id)
            .first()
        )
    return None
