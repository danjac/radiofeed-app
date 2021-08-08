from __future__ import annotations

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

    # close current running episode first
    AudioLog.objects.playing(request.user).update(
        is_playing=False,
        updated=timezone.now(),
    )

    return render_player_start(
        request, get_episode_or_404(request, episode_id, with_podcast=True)
    )


@require_POST
@hx_login_required
def close_player(request: HttpRequest) -> HttpResponse:
    AudioLog.objects.playing(request.user).update(
        is_playing=False,
        updated=timezone.now(),
    )
    return render_player_close(request)


@require_POST
@hx_login_required
def play_next_episode(request: HttpRequest) -> HttpResponse:
    """Marks current episode complete, starts next episode in queue
    or closes player if queue empty."""

    now = timezone.now()

    AudioLog.objects.playing(request.user).update(
        is_playing=False,
        updated=now,
        completed=now,
        current_time=0,
    )

    if request.user.autoplay and (
        next_item := (
            QueueItem.objects.filter(user=request.user)
            .select_related("episode", "episode__podcast")
            .order_by("position")
            .first()
        )
    ):
        return render_player_start(request, next_item.episode)
    return render_player_close(request)


@require_safe
@hx_login_required
def reload_player(request: HttpRequest) -> HttpResponse:
    return render_player(
        request,
        {
            "log": AudioLog.objects.playing(request.user)
            .select_related("episode", "episode__podcast")
            .first()
        },
    )


@require_POST
@ratelimit(key="ip", rate="20/m")
@hx_login_required
def player_time_update(request: HttpRequest) -> HttpResponse:
    """Update current play time of episode"""
    try:
        AudioLog.objects.playing(request.user).update(
            current_time=int(request.POST["current_time"]),
            updated=timezone.now(),
        )
        return HttpResponseNoContent()
    except (KeyError, ValueError):
        return HttpResponseBadRequest()


def render_player_start(request: HttpRequest, episode: Episode) -> HttpResponse:

    QueueItem.objects.filter(
        user=request.user,
        episode=episode,
    ).delete()

    log, _ = AudioLog.objects.update_or_create(
        episode=episode,
        user=request.user,
        defaults={
            "is_playing": True,
            "completed": None,
            "updated": timezone.now(),
        },
    )

    return with_hx_trigger(
        render_player(
            request,
            {
                "log": log,
                "episode": episode,
                "autoplay": True,
            },
        ),
        {
            "remove-queue-item": episode.id,
            "play-episode": episode.id,
        },
    )


def render_player_close(request: HttpRequest) -> HttpResponse:
    return with_hx_trigger(render_player(request), "close-player")


def render_player(
    request: HttpRequest, extra_context: dict | None = None
) -> HttpResponse:
    return TemplateResponse(request, "episodes/_player.html", extra_context)
