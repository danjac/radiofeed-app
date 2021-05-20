from typing import Literal

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST, require_safe

from audiotrails.shared.decorators import accepts_json, ajax_login_required
from audiotrails.shared.response import HttpResponseNoContent

from ..models import QueueItem
from . import get_episode_or_404


@require_safe
@login_required
def index(request: HttpRequest) -> HttpResponse:
    return TemplateResponse(
        request,
        "episodes/queue.html",
        {
            "queue_items": QueueItem.objects.filter(user=request.user)
            .select_related("episode", "episode__podcast")
            .order_by("position"),
        },
    )


@require_POST
@ajax_login_required
def add_to_queue(
    request: HttpRequest, episode_id: int, to=Literal["start", "end"]
) -> HttpResponse:

    episode = get_episode_or_404(request, episode_id, with_podcast=True)
    response = HttpResponseNoContent()

    # can't add to queue if currently playing
    if request.player.is_playing(episode):
        return response

    try:
        if to == "start":
            QueueItem.objects.add_item_to_start(request.user, episode)
        else:
            QueueItem.objects.add_item_to_end(request.user, episode)
    except IntegrityError:
        pass

    return response


@require_POST
@ajax_login_required
def remove_from_queue(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id)
    QueueItem.objects.filter(episode=episode, user=request.user).delete()
    response = HttpResponseNoContent()
    response["HX-Trigger"] = "reload-queue"
    return response


@require_POST
@accepts_json
@ajax_login_required
def move_queue_items(request: HttpRequest) -> HttpResponse:

    try:
        QueueItem.objects.move_items(
            request.user, [int(item) for item in request.json["items"]]
        )
    except (KeyError, TypeError, ValueError):
        return HttpResponseBadRequest("Invalid payload")

    return HttpResponseNoContent()
