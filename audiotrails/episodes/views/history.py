import http

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_POST, require_safe

from audiotrails.shared.decorators import ajax_login_required
from audiotrails.shared.pagination import render_paginated_response

from ..models import AudioLog
from . import get_episode_or_404


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
@ajax_login_required
def remove_audio_log(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id)

    response = HttpResponse(status=http.HTTPStatus.NO_CONTENT)

    # you shouldn't be able to remove history if episode currently playing
    if not request.player.is_playing(episode):
        AudioLog.objects.filter(user=request.user, episode=episode).delete()
        response["HX-Trigger"] = "reload-history"
    return response
