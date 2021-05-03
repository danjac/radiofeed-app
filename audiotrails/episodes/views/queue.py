import http

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db import IntegrityError
from django.db.models import Max
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from ..models import QueueItem
from . import get_episode_or_404


@login_required
def index(request):
    return TemplateResponse(
        request,
        "episodes/queue.html",
        {
            "queue_items": QueueItem.objects.filter(user=request.user)
            .select_related("episode", "episode__podcast")
            .order_by("position")
        },
    )


@require_POST
def add_to_queue(request, episode_id):

    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    if request.user.is_anonymous:
        return redirect_to_login(episode.get_absolute_url())

    items = QueueItem.objects.filter(user=request.user)

    try:
        QueueItem.objects.create(
            user=request.user,
            episode=episode,
            position=(items.aggregate(Max("position"))["position__max"] or 0) + 1,
        )
    except IntegrityError:
        pass

    return render_toggle_redirect(request)


@require_POST
def remove_from_queue(request, episode_id):
    episode = get_episode_or_404(request, episode_id)
    QueueItem.objects.filter(episode=episode, user=request.user).delete()

    # tbd: just raise PermissionDenied (button should be simple login page link)
    if request.user.is_anonymous:
        return redirect_to_login(episode.get_absolute_url())

    # TBD: htmx should pass target, if present then re-render that section
    # ie. queue page
    # otherwise just re-render toggle

    # play button: we keep track of individual queue items with a counter
    # in top level queue component
    # on @open-player() dispatch 'remove-play-queue'
    # when counter == 0 then show "empty" section
    return render_toggle_redirect(request)


@require_POST
def move_queue_items(request):

    if request.user.is_anonymous:
        return HttpResponseForbidden("You must be logged in")

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


def render_toggle_redirect(request):
    if not (
        redirect_url := request.POST.get("redirect_url")
    ) or not url_has_allowed_host_and_scheme(
        redirect_url, {request.get_host()}, require_https=not settings.DEBUG
    ):
        redirect_url = reverse("episodes:queue")

    return redirect(redirect_url)
