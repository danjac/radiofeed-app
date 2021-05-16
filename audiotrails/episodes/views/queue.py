import http

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Max
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

from audiotrails.shared.decorators import accepts_json, ajax_login_required

from ..models import Episode, QueueItem
from . import get_episode_or_404


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
def add_to_queue(request: HttpRequest, episode_id: int) -> HttpResponse:

    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    items = QueueItem.objects.filter(user=request.user)

    try:
        QueueItem.objects.create(
            user=request.user,
            episode=episode,
            position=(items.aggregate(Max("position"))["position__max"] or 0) + 1,
        )
    except IntegrityError:
        pass

    return render_queue_toggle(request, episode, True)


@require_POST
@ajax_login_required
def remove_from_queue(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id)
    QueueItem.objects.filter(episode=episode, user=request.user).delete()
    return render_queue_toggle(request, episode, False)


@require_POST
@accepts_json
@ajax_login_required
def move_queue_items(request: HttpRequest) -> HttpResponse:

    qs = QueueItem.objects.filter(user=request.user)
    items = qs.in_bulk()
    for_update = []

    try:
        for position, item_id in enumerate(request.json["items"], 1):
            if item := items[int(item_id)]:
                item.position = position
                for_update.append(item)
    except (KeyError, TypeError, ValueError):
        return HttpResponseBadRequest("Invalid payload")

    qs.bulk_update(for_update, ["position"])
    return HttpResponse(status=http.HTTPStatus.NO_CONTENT)


def render_queue_toggle(
    request: HttpRequest, episode: Episode, is_queued: bool
) -> HttpResponse:
    response = HttpResponse(status=http.HTTPStatus.NO_CONTENT)
    response["HX-Trigger"] = "reload-queue"
    return response
