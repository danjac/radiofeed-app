import http
import json

from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.views.decorators.http import require_POST

from ..models import QueueItem
from . import get_episode_or_404


@require_POST
def start_player(request, episode_id):
    if request.user.is_anonymous:
        return HttpResponseForbidden("not logged in")

    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    return JsonResponse(request.player.start_episode(episode).to_json())


@require_POST
def close_player(request):
    if request.user.is_anonymous:
        return HttpResponseForbidden("not logged in")
    request.player.stop_episode()
    return JsonResponse({})


@require_POST
def play_next_episode(request):
    """Marks current episode complete, starts next episode in queue
    or closes player if queue empty."""
    if request.user.is_anonymous:
        return HttpResponseForbidden("not logged in")

    if next_item := (
        QueueItem.objects.filter(user=request.user)
        .with_current_time(request.user)
        .select_related("episode", "episode__podcast")
        .order_by("position")
        .first()
    ):
        return JsonResponse(request.player.start_episode(next_item.episode).to_json())

    return JsonResponse({})


@require_POST
def player_update_current_time(request):
    """Update current play time of episode"""
    if request.user.is_anonymous:
        return HttpResponseForbidden("not logged in")
    try:
        request.player.update_current_time(
            float(json.loads(request.body)["currentTime"])
        )
        return HttpResponse(status=http.HTTPStatus.NO_CONTENT)
    except (KeyError, ValueError):
        return HttpResponseBadRequest("missing or invalid data")
