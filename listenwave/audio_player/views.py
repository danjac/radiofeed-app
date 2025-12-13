import http
from typing import TypedDict

from django.db import IntegrityError
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from pydantic import BaseModel, ValidationError

from listenwave.request import HttpRequest, is_authenticated_request


class PlayerUpdate(BaseModel):
    """Data model for player time update."""

    current_time: int
    duration: int


class PlayerUpdateError(TypedDict):
    """Data model for player error response."""

    error: str


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
