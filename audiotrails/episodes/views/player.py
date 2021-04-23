import http

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.http import require_POST
from turbo_response import TurboStream
from turbo_response.decorators import turbo_stream_response

from ..models import AudioLog, QueueItem
from . import get_episode_or_404
from .history import render_remove_audio_log
from .queue import render_queue_toggle, render_remove_from_queue


@require_POST
def start_player(
    request,
    episode_id,
):

    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    if request.user.is_anonymous:
        return redirect_to_login(episode.get_absolute_url())

    return render_player_response(request, episode)


@require_POST
def close_player(request):
    if request.user.is_anonymous:
        return redirect_to_login(settings.HOME_URL)

    return render_player_response(request)


@require_POST
def play_next_episode(request):
    """Marks current episode complete, starts next episode in queue
    or closes player if queue empty."""
    if request.user.is_anonymous:
        return redirect_to_login(settings.HOME_URL)

    if next_item := (
        QueueItem.objects.filter(user=request.user)
        .with_current_time(request.user)
        .select_related("episode", "episode__podcast")
        .order_by("position")
        .first()
    ):
        next_episode = next_item.episode
    else:
        next_episode = None

    return render_player_response(request, next_episode, mark_completed=True)


@require_POST
def player_update_current_time(request):
    """Update current play time of episode"""
    if request.user.is_anonymous:
        return HttpResponseForbidden("not logged in")
    try:
        AudioLog.objects.filter(
            episode=request.session["player_episode"], user=request.user
        ).update(current_time=round(float(request.POST["current_time"])))
        return HttpResponse(status=http.HTTPStatus.NO_CONTENT)
    except (KeyError, ValueError):
        pass
    return HttpResponseBadRequest("missing or invalid data")


def render_player_toggle(request, episode, is_playing):
    return (
        TurboStream(episode.dom.player_toggle)
        .replace.template(
            "episodes/_player_toggle.html",
            {
                "episode": episode,
                "is_playing": is_playing,
            },
        )
        .render(request=request)
    )


@turbo_stream_response
def render_player_response(request, next_episode=None, mark_completed=False):

    streams = []

    now = timezone.now()

    if request.POST.get("is_modal"):
        streams += [TurboStream("modal").replace.template("_modal.html").render()]

    if (episode_id := request.session.pop("player_episode", None)) and (
        log := AudioLog.objects.filter(user=request.user, episode=episode_id)
        .select_related("episode")
        .first()
    ):
        log.updated = now

        if mark_completed:
            log.completed = now
            log.current_time = 0

        log.save()

        streams += [
            render_player_toggle(request, log.episode, False),
            render_remove_audio_log(request, log.episode, False),
        ]

    if next_episode:
        AudioLog.objects.update_or_create(
            episode=next_episode,
            user=request.user,
            defaults={
                "updated": now,
                "completed": None,
            },
        )

        request.session["player_episode"] = next_episode.id

        streams += [
            render_remove_from_queue(request, next_episode),
            render_queue_toggle(request, next_episode, False),
            render_player_toggle(request, next_episode, True),
            render_remove_audio_log(request, next_episode, True),
        ]

    return streams + [
        TurboStream("player")
        .replace.template(
            "episodes/_player.html",
            {
                "new_episode": next_episode,
            },
        )
        .render(request=request)
    ]
