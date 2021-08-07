from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe
from ratelimit.decorators import ratelimit

from jcasts.episodes.models import AudioLog, Episode, QueueItem
from jcasts.episodes.views import get_episode_or_404
from jcasts.shared.decorators import hx_login_required
from jcasts.shared.response import HttpResponseNoContent, with_hx_trigger


@require_POST
@hx_login_required
def start_player(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id, with_podcast=True)
    request.player.start_episode(episode)
    return render_player(request, episode)


@require_POST
@hx_login_required
def close_player(request: HttpRequest) -> HttpResponse:
    request.player.stop_episode()
    return render_player(request)


@require_POST
@hx_login_required
def play_next_episode(request: HttpRequest) -> HttpResponse:
    """Marks current episode complete, starts next episode in queue
    or closes player if queue empty."""

    request.player.stop_episode(mark_completed=True)

    if request.user.autoplay and (
        next_item := (
            QueueItem.objects.filter(user=request.user)
            .with_current_time(request.user)
            .select_related("episode", "episode__podcast")
            .order_by("position")
            .first()
        )
    ):
        next_episode = next_item.episode
        request.player.start_episode(next_episode)
    else:
        next_episode = None

    return render_player(request, next_episode)


@hx_login_required
@require_safe
def reload_player(request: HttpRequest) -> HttpResponse:
    return render_player(request)


@require_POST
@hx_login_required
def mark_complete(request: HttpRequest, episode_id: int) -> HttpResponse:
    AudioLog.objects.filter(
        episode=episode_id,
        user=request.user,
        autoplay=False,
        completed__isnull=True,
    ).update(completed=timezone.now())

    messages.info(request, "Episode marked complete")
    return HttpResponseNoContent()


@require_POST
@ratelimit(key="ip", rate="20/m")
@hx_login_required
def player_time_update(request: HttpRequest) -> HttpResponse:
    """Update current play time of episode"""
    try:
        request.player.update_current_time(float(request.POST["current_time"]))
        return HttpResponseNoContent()
    except (KeyError, ValueError):
        return HttpResponseBadRequest("missing or invalid data")


def render_player(
    request: HttpRequest,
    next_episode: Episode | None = None,
) -> HttpResponse:

    response = TemplateResponse(
        request, "_player.html", {"autoplay": next_episode is not None}
    )

    if request.method == "POST":
        if next_episode:
            return with_hx_trigger(
                response,
                {
                    "remove-queue-item": next_episode.id,
                    "play-episode": next_episode.id,
                },
            )
        return with_hx_trigger(response, "close-player")

    return response
