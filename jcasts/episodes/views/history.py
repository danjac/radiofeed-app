from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe

from jcasts.episodes.models import AudioLog
from jcasts.shared.decorators import hx_login_required
from jcasts.shared.pagination import render_paginated_response
from jcasts.shared.response import HttpResponseNoContent, with_hx_trigger


@require_safe
@login_required
def index(request: HttpRequest) -> HttpResponse:

    logs = (
        AudioLog.objects.filter(user=request.user)
        .select_related("episode", "episode__podcast")
        .order_by("-updated")
    )

    if request.search:
        logs = logs.search(request.search).order_by("-rank", "-updated")
    else:
        logs = logs.order_by("-updated")

    return render_paginated_response(
        request,
        logs,
        "episodes/history.html",
        "episodes/_history.html",
    )


@require_POST
@hx_login_required
def mark_complete(request: HttpRequest, episode_id: int) -> HttpResponse:

    if episode_id != request.player.get_episode():
        AudioLog.objects.filter(
            user=request.user, episode=episode_id, completed__isnull=True
        ).update(
            completed=timezone.now(),
            current_time=0,
        )

        messages.info(request, "Episode marked complete")
    return HttpResponseNoContent()


@require_POST
@hx_login_required
def remove_audio_log(request: HttpRequest, episode_id: int) -> HttpResponse:
    if episode_id != request.player.get_episode():
        AudioLog.objects.filter(user=request.user, episode=episode_id).delete()
        messages.info(request, "Removed from History")
    return with_hx_trigger(HttpResponseNoContent(), {"remove-audio-log": episode_id})
