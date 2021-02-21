import http
from typing import List

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Max, QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

from turbo_response import TurboStream

from radiofeed.users.decorators import ajax_login_required

from ..models import Episode, QueueItem
from . import get_episode_or_404


@login_required
def index(request: HttpRequest) -> HttpResponse:
    return TemplateResponse(
        request,
        "episodes/queue/index.html",
        {"queue_items": get_queue_items(request)},
    )


@require_POST
@login_required
def add_to_queue(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(episode_id)
    position = (
        QueueItem.objects.filter(user=request.user).aggregate(Max("position"))[
            "position__max"
        ]
        or 0
    ) + 1

    try:
        QueueItem.objects.create(user=request.user, episode=episode, position=position)
    except IntegrityError:
        pass

    return render_queue_response(request, episode, True)


@require_POST
@login_required
def remove_from_queue(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(episode_id)
    items = QueueItem.objects.filter(user=request.user)
    items.filter(episode=episode).delete()

    if "remove" in request.POST:
        if items.count() == 0:
            return TurboStream("queue").replace.response("Your Play Queue is now empty")
        return TurboStream(episode.get_queue_dom_id()).remove.response()
    return render_queue_response(request, episode, False)


@require_POST
@ajax_login_required
def move_queue_items(request: HttpRequest) -> HttpResponse:

    qs = QueueItem.objects.filter(user=request.user)
    items = qs.in_bulk()
    for_update = []

    try:
        for position, item_id in enumerate(request.POST.getlist("items"), 1):
            if item := items[int(item_id)]:
                item.position = position
                for_update.append(item)
    except (KeyError, ValueError):
        return HttpResponseBadRequest("Invalid payload")

    qs.bulk_update(for_update, ["position"])
    return HttpResponse(status=http.HTTPStatus.NO_CONTENT)


def render_queue_response(
    request: HttpRequest, episode: Episode, is_queued: bool
) -> List[str]:
    return (
        TurboStream(episode.get_queue_toggle_id())
        .replace.template(
            "episodes/components/_queue_toggle.html",
            {
                "episode": episode,
                "is_queued": is_queued,
            },
        )
        .response(request)
    )


def get_queue_items(request: HttpRequest) -> QuerySet:
    return (
        QueueItem.objects.filter(user=request.user)
        .select_related("episode", "episode__podcast")
        .order_by("position")
    )
