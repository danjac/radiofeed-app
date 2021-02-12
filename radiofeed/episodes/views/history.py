from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

from turbo_response import TurboStream

from radiofeed.pagination import render_paginated_response

from ..models import AudioLog
from . import get_episode_or_404


@login_required
def index(request: HttpRequest) -> HttpResponse:

    if request.turbo.frame:

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
            request, logs, "episodes/history/_episode_list.html"
        )

    return TemplateResponse(request, "episodes/history/index.html")


@require_POST
@login_required
def remove_history(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(episode_id)

    logs = AudioLog.objects.filter(user=request.user)

    logs.filter(episode=episode).delete()

    if logs.count() == 0:
        return TurboStream("history").replace.response("Your History is now empty.")

    return TurboStream(episode.get_history_dom_id()).remove.response()
