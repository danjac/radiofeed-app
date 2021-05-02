from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from audiotrails.shared.pagination import render_paginated_response

from ..models import AudioLog
from . import get_episode_or_404


@login_required
def index(request):

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
def remove_audio_log(request, episode_id):
    episode = get_episode_or_404(request, episode_id)

    if request.user.is_anonymous:
        return redirect_to_login(episode.get_absolute_url())

    AudioLog.objects.filter(user=request.user, episode=episode).delete()

    messages.info(request, "Episode has been removed from your history")
    return redirect("episodes:history")
