from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from turbo_response import TurboStream

from ..models import Episode


def get_episode_or_404(episode_id: int) -> Episode:
    return get_object_or_404(Episode, pk=episode_id)


def get_episode_detail_or_404(request: HttpRequest, episode_id: int) -> Episode:
    return get_object_or_404(
        Episode.objects.with_current_time(request.user).select_related("podcast"),
        pk=episode_id,
    )


def render_close_modal() -> str:
    return TurboStream("modal").update.render()
