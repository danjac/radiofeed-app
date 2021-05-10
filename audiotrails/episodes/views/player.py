import http
import json

from django.http import HttpResponse, HttpResponseBadRequest
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

from audiotrails.shared.decorators import ajax_login_required

from ..models import QueueItem
from . import get_episode_or_404


@require_POST
@ajax_login_required
def start_player(request, episode_id):
    episode = get_episode_or_404(request, episode_id, with_podcast=True)
    request.player.start_episode(episode)
    return render_player(request, episode)


@require_POST
@ajax_login_required
def close_player(request):
    request.player.stop_episode()
    return render_player(request)


@require_POST
@ajax_login_required
def play_next_episode(request):
    """Marks current episode complete, starts next episode in queue
    or closes player if queue empty."""

    request.player.stop_episode(mark_completed=True)

    if next_item := (
        QueueItem.objects.filter(user=request.user)
        .with_current_time(request.user)
        .select_related("episode", "episode__podcast")
        .order_by("position")
        .first()
    ):
        request.player.start_episode(next_item.episode)
        episode = next_item.episode
    else:
        episode = None

    return render_player(request, episode)


@require_POST
@ajax_login_required
def player_time_update(request):
    """Update current play time of episode"""
    try:
        request.player.update_current_time(float(request.POST["current_time"]))
        return HttpResponse(status=http.HTTPStatus.NO_CONTENT)
    except (KeyError, ValueError):
        return HttpResponseBadRequest("missing or invalid data")


def render_player(request, episode=None):
    response = TemplateResponse(
        request, "_player.html", {"run_immediately": episode is not None}
    )
    events = {"reload-episode": ""}
    if episode:
        events["reload-queue"] = ""
    response["HX-Trigger"] = json.dumps(events)
    response["HX-Trigger-After-Settle"] = "close-modal"
    return response
