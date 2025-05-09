import contextlib
from typing import Literal

from django import template
from django.http import HttpRequest
from django.template.context import RequestContext

from radiofeed import cover_image
from radiofeed.episodes.models import AudioLog, Episode

register = template.Library()


@register.inclusion_tag("episodes/audio_player.html", takes_context=True)
def audio_player(
    context: RequestContext,
    audio_log: AudioLog | None = None,
    action: Literal["load", "play", "close"] = "load",
) -> dict:
    """Renders the audio player."""

    context_dct = {
        "request": context.request,
        "action": action,
    }

    if (
        context.request.user.is_authenticated
        and action in ("load", "play")
        and (audio_log := audio_log or _get_audio_log(context.request))
    ):
        return context_dct | {
            "audio_log": audio_log,
            "metadata": _get_media_metadata(context.request, audio_log.episode),
        }

    return context_dct


def _get_audio_log(request: HttpRequest) -> AudioLog | None:
    if request.user.is_authenticated and (episode_id := request.player.get()):
        with contextlib.suppress(AudioLog.DoesNotExist):
            return request.user.audio_logs.select_related(
                "episode",
                "episode__podcast",
            ).get(episode_id=episode_id)
    return None


def _get_media_metadata(request: HttpRequest, episode: Episode) -> dict:
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
            request,
            episode.get_cover_url(),
        ),
    }
