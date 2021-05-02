import http

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.views.decorators.http import require_POST

from ..models import QueueItem
from . import get_episode_or_404

# from .history import render_remove_audio_log_btn

# from .queue import render_queue_toggle, render_remove_from_queue


"""
Overview:

When "play episode":
    - return JsonResponse
    - Alpine component creates player
"""


@require_POST
def start_player(request, episode_id):

    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    # tbd: we just need a decorator to raise PermissionDenied
    if request.user.is_anonymous:
        return redirect_to_login(episode.get_absolute_url())

    return JsonResponse(request.player.start_episode(episode).to_json())


@require_POST
def close_player(request):
    if request.user.is_anonymous:
        return redirect_to_login(settings.HOME_URL)
    request.player.stop_episode()
    return JsonResponse({})


@require_POST
def play_next_episode(request):
    """Marks current episode complete, starts next episode in queue
    or closes player if queue empty."""
    if request.user.is_anonymous:
        return redirect_to_login(settings.HOME_URL)

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
        request.player.update_current_time(float(request.POST["current_time"]))
        return HttpResponse(status=http.HTTPStatus.NO_CONTENT)
    except (KeyError, ValueError):
        return HttpResponseBadRequest("missing or invalid data")
