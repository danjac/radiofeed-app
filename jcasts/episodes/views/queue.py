from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseBadRequest
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods

from jcasts.episodes.models import QueueItem
from jcasts.episodes.views import get_episode_or_404
from jcasts.shared.decorators import ajax_login_required
from jcasts.shared.htmx import with_hx_trigger
from jcasts.shared.response import HttpResponseConflict


@require_http_methods(["GET"])
@login_required
def index(request):
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
def add_to_queue(request, episode_id, to):

    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    if not request.player.has(episode.id):

        try:
            if to == "start":
                QueueItem.objects.add_item_to_start(request.user, episode)
            else:
                QueueItem.objects.add_item_to_end(request.user, episode)
            messages.success(request, "Added to Play Queue")
        except IntegrityError:
            return HttpResponseConflict()

    return with_hx_trigger(HttpResponse(), {"actions-close": episode.id})


@require_http_methods(["DELETE"])
@ajax_login_required
def remove_from_queue(request, episode_id):
    episode = get_episode_or_404(request, episode_id)
    QueueItem.objects.filter(user=request.user).filter(episode=episode).delete()
    messages.info(request, "Removed from Play Queue")

    return with_hx_trigger(
        HttpResponse(),
        {
            "actions-close": episode.id,
            "remove-queue-item": episode.id,
        },
    )


@require_http_methods(["POST"])
@ajax_login_required
def move_queue_items(request):

    try:
        QueueItem.objects.move_items(
            request.user, [int(item) for item in request.POST.getlist("items")]
        )
    except ValueError:
        return HttpResponseBadRequest("Invalid payload")

    return HttpResponse()
