import http
from typing import List

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Max
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

from turbo_response import TurboStream, TurboStreamResponse

from radiofeed.streams import (
    render_close_modal,
    render_info_message,
    render_success_message,
)
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

    return TurboStreamResponse(
        [
            render_close_modal(),
            render_success_message("You have added this episode to your Play Queue"),
        ]
        + render_queue_streams(request, episode, True)
    )


@require_POST
@login_required
def remove_from_queue(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(episode_id)
    QueueItem.objects.filter(episode=episode, user=request.user).delete()

    return TurboStreamResponse(
        [
            render_close_modal(),
            render_info_message("You have removed this episode from your Play Queue"),
        ]
        + render_queue_streams(request, episode, False)
    )


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


def render_queue_streams(
    request: HttpRequest, episode: Episode, is_queued: bool
) -> List[str]:
    streams = [
        TurboStream(episode.get_queue_toggle_id())
        .replace.template(
            "episodes/queue/_toggle.html",
            {"episode": episode, "is_queued": is_queued},
            request=request,
        )
        .render(),
    ]

    if not is_queued:
        streams += [
            TurboStream(episode.get_queue_dom_id()).remove.render(),
        ]
        if QueueItem.objects.filter(user=request.user).count() == 0:
            streams += [TurboStream("queue").append.render("Your queue is now empty.")]

    return streams
