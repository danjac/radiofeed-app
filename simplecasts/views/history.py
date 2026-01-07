from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST, require_safe

from simplecasts.http.decorators import require_DELETE
from simplecasts.http.request import AuthenticatedHttpRequest
from simplecasts.models import AudioLog
from simplecasts.views.paginator import render_paginated_response


@require_safe
@login_required
def history(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """Renders user's listening history. User can also search history."""
    audio_logs = request.user.audio_logs.select_related("episode", "episode__podcast")

    ordering = request.GET.get("order", "desc")
    order_by = "listened" if ordering == "asc" else "-listened"

    if request.search:
        audio_logs = audio_logs.search(request.search.value).order_by("-rank", order_by)
    else:
        audio_logs = audio_logs.order_by(order_by)

    return render_paginated_response(
        request,
        "episodes/history.html",
        audio_logs,
        {
            "ordering": ordering,
        },
    )


@require_POST
@login_required
def mark_complete(
    request: AuthenticatedHttpRequest, episode_id: int
) -> TemplateResponse:
    """Marks audio log complete."""

    if request.player.has(episode_id):
        raise Http404

    audio_log = get_object_or_404(
        request.user.audio_logs.select_related("episode"),
        episode__pk=episode_id,
    )

    audio_log.current_time = 0
    audio_log.save()

    messages.success(request, "Episode marked complete")

    return _render_audio_log_action(request, audio_log, show_audio_log=True)


@require_DELETE
@login_required
def remove_audio_log(
    request: AuthenticatedHttpRequest, episode_id: int
) -> TemplateResponse:
    """Removes audio log from user history and returns HTMX snippet."""
    # cannot remove episode if in player
    if request.player.has(episode_id):
        raise Http404

    audio_log = get_object_or_404(
        request.user.audio_logs.select_related("episode"),
        episode__pk=episode_id,
    )

    audio_log.delete()

    messages.info(request, "Removed from History")

    return _render_audio_log_action(request, audio_log, show_audio_log=False)


def _render_audio_log_action(
    request: AuthenticatedHttpRequest,
    audio_log: AudioLog,
    *,
    show_audio_log: bool,
) -> TemplateResponse:
    context = {"episode": audio_log.episode}

    if show_audio_log:
        context["audio_log"] = audio_log

    return TemplateResponse(request, "episodes/detail.html#audio_log", context)
