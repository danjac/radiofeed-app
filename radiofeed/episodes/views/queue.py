import http
from typing import List

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Max
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

from turbo_response import TurboStream, TurboStreamResponse
from turbo_response.stream import TurboStreamTemplate

from radiofeed.users.decorators import ajax_login_required

from ..models import Episode, QueueItem
from . import get_episode_or_404


@login_required
def index(request: HttpRequest) -> HttpResponse:
    return TemplateResponse(
        request,
        "episodes/queue/index.html",
        {
            "queue_items": QueueItem.objects.filter(user=request.user)
            .select_related("episode", "episode__podcast")
            .order_by("position")
        },
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

    return render_episode_queue_response(request, episode, True)


@require_POST
@login_required
def remove_from_queue(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(episode_id)
    QueueItem.objects.filter(user=request.user, episode=episode).delete()
    if "remove" in request.POST:
        return TurboStreamResponse(render_remove_from_queue_streams(request, episode))
    return render_episode_queue_response(request, episode, False)


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


def episode_queue_stream_template(
    episode: Episode, is_queued: bool
) -> TurboStreamTemplate:

    return TurboStream(episode.get_queue_toggle_id()).replace.template(
        "episodes/queue/_toggle.html",
        {"episode": episode, "is_queued": is_queued},
    )


def render_remove_from_queue_streams(
    request: HttpRequest, episode: Episode
) -> List[str]:
    streams = [
        TurboStream(f"queue-item-{episode.id}").remove.render(),
        episode_queue_stream_template(episode, False).render(),
    ]
    if QueueItem.objects.filter(user=request.user).count() == 0:
        streams += [
            TurboStream("queue").append.render("No more items left in queue"),
        ]
    return streams


def render_episode_queue_response(
    request: HttpRequest, episode: Episode, is_queued: bool
) -> HttpResponse:
    if request.turbo:
        return episode_queue_stream_template(episode, is_queued).response(request)
    return redirect(episode)
