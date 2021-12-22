from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods

from jcasts.episodes.models import QueueItem
from jcasts.episodes.views import get_episode_or_404
from jcasts.shared.decorators import ajax_login_required
from jcasts.shared.response import HttpResponseConflict, HttpResponseNoContent


@require_http_methods(["GET"])
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


@require_http_methods(["POST"])
@ajax_login_required
def add_to_queue(
    request: HttpRequest, episode_id: int, add_to_start: bool
) -> HttpResponse:

    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    if not request.player.has(episode.id):

        try:
            QueueItem.objects.create_item(request.user, episode, add_to_start)
            messages.success(request, "Added to Play Queue")
        except IntegrityError:
            return HttpResponseConflict()

    return HttpResponseNoContent()


@require_http_methods(["DELETE"])
@ajax_login_required
def remove_from_queue(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id)
    QueueItem.objects.filter(user=request.user).filter(episode=episode).delete()
    messages.info(request, "Removed from Play Queue")

    return HttpResponseNoContent()


@require_http_methods(["POST"])
@ajax_login_required
def move_queue_items(request: HttpRequest) -> HttpResponse:

    try:
        QueueItem.objects.move_items(
            request.user, [int(item) for item in request.POST.getlist("items")]
        )
    except ValueError:
        return HttpResponseBadRequest("Invalid payload")

    return HttpResponseNoContent()
