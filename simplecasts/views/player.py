import http
from typing import Literal, TypedDict

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from pydantic import BaseModel, ValidationError

from simplecasts.http.request import (
    AuthenticatedHttpRequest,
    HttpRequest,
    is_authenticated_request,
)
from simplecasts.http.response import HttpResponseNoContent
from simplecasts.models import AudioLog, Episode

PlayerAction = Literal["load", "play", "close"]


class PlayerUpdate(BaseModel):
    """Data model for player time update."""

    current_time: int
    duration: int


class PlayerUpdateError(TypedDict):
    """Data model for player error response."""

    error: str


@require_POST
@login_required
def start_player(
    request: AuthenticatedHttpRequest, episode_id: int
) -> TemplateResponse:
    """Starts player. Creates new audio log if required."""
    episode = get_object_or_404(
        Episode.objects.select_related("podcast"),
        pk=episode_id,
    )

    audio_log, _ = request.user.audio_logs.update_or_create(
        episode=episode,
        defaults={
            "listened": timezone.now(),
        },
    )

    request.player.set(episode.pk)

    return _render_player_action(request, audio_log, action="play")


@require_POST
@login_required
def close_player(
    request: AuthenticatedHttpRequest,
) -> TemplateResponse | HttpResponseNoContent:
    """Closes audio player."""
    if episode_id := request.player.pop():
        audio_log = get_object_or_404(
            request.user.audio_logs.select_related("episode"),
            episode__pk=episode_id,
        )
        return _render_player_action(request, audio_log, action="close")
    return HttpResponseNoContent()


@require_POST
def player_time_update(request: HttpRequest) -> JsonResponse:
    """Handles player time update AJAX requests."""

    if not is_authenticated_request(request):
        return JsonResponse(
            PlayerUpdateError(error="Authentication required"),
            status=http.HTTPStatus.UNAUTHORIZED,
        )

    episode_id = request.player.get()

    if episode_id is None:
        return JsonResponse(
            PlayerUpdateError(error="No episode in player"),
            status=http.HTTPStatus.BAD_REQUEST,
        )

    try:
        update = PlayerUpdate.model_validate_json(request.body)
    except ValidationError as exc:
        return JsonResponse(
            PlayerUpdateError(error=exc.json()),
            status=http.HTTPStatus.BAD_REQUEST,
        )

    try:
        request.user.audio_logs.update_or_create(
            episode_id=episode_id,
            defaults={
                "listened": timezone.now(),
                "current_time": update.current_time,
                "duration": update.duration,
            },
        )

    except IntegrityError:
        return JsonResponse(
            PlayerUpdateError(error="Update cannot be saved"),
            status=http.HTTPStatus.CONFLICT,
        )

    return JsonResponse(update.model_dump())


def _render_player_action(
    request: HttpRequest,
    audio_log: AudioLog,
    *,
    action: PlayerAction,
) -> TemplateResponse:
    return TemplateResponse(
        request,
        "episodes/detail.html#audio_player_button",
        {
            "action": action,
            "audio_log": audio_log,
            "episode": audio_log.episode,
            "is_playing": action == "play",
        },
    )
