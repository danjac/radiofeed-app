from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from django import template

from radiofeed.covers import get_metadata_info

register = template.Library()

if TYPE_CHECKING:  # pragma: no check
    from django.template.context import RequestContext

    from radiofeed.episodes.models import AudioLog, Episode


@dataclasses.dataclass
class PlayerInfo:
    """Audio player context data."""

    current_time: int | None = None
    episode: Episode | None = None
    is_playing: bool = False
    start_player: bool = False
    hx_oob: bool = False

    def update(self, **fields) -> PlayerInfo:
        """Update instance."""
        return dataclasses.replace(self, **fields)

    def merge_context(self, context: RequestContext) -> dict:
        """Merges info to context."""
        return context.flatten() | dataclasses.asdict(self)


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
    info = PlayerInfo()

    if (
        context.request.user.is_authenticated
        and (episode_id := context.request.player.get())
        and (
            audio_log := context.request.user.audio_logs.filter(episode__pk=episode_id)
            .select_related(
                "episode",
                "episode__podcast",
            )
            .first()
        )
    ):
        info = info.update(
            episode=audio_log.episode,
            current_time=audio_log.current_time,
            is_playing=True,
        )

    return info.merge_context(context)


@register.inclusion_tag("episodes/_audio_player.html#player", takes_context=True)
def update_audio_player(
    context: RequestContext,
    audio_log: AudioLog | None = None,
    *,
    start_player: bool,
) -> dict:
    """Renders audio player update to open or close the player."""
    info = PlayerInfo(hx_oob=True)
    if audio_log and start_player:
        info = info.update(
            current_time=audio_log.current_time,
            episode=audio_log.episode,
            start_player=True,
            is_playing=True,
        )
    return info.merge_context(context)
