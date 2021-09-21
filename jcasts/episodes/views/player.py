from django.http import HttpResponse, HttpResponseBadRequest
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from ratelimit.decorators import ratelimit

from jcasts.episodes.models import AudioLog, QueueItem
from jcasts.episodes.views import get_episode_or_404
from jcasts.shared.decorators import ajax_login_required
from jcasts.shared.htmx import with_hx_trigger
from jcasts.shared.response import HttpResponseNoContent


@require_http_methods(["POST"])
@ajax_login_required
def start_player(request, episode_id):
    return render_start_player(
        request, get_episode_or_404(request, episode_id, with_podcast=True)
    )


@require_http_methods(["POST"])
@ajax_login_required
def close_player(request):
    request.player.remove()
    AudioLog.objects.filter(user=request.user).update(is_playing=False)
    return render_close_player(request)


@require_http_methods(["POST"])
@ajax_login_required
def play_next_episode(request):
    """Marks current episode complete, starts next episode in queue
    or closes player if queue empty."""

    if episode_id := request.player.remove():

        now = timezone.now()

        AudioLog.objects.filter(user=request.user, episode=episode_id).update(
            updated=now,
            completed=now,
            current_time=0,
            is_playing=False,
        )

    if request.user.autoplay and (
        next_item := (
            QueueItem.objects.filter(user=request.user)
            .select_related("episode", "episode__podcast")
            .order_by("position")
            .first()
        )
    ):
        return render_start_player(request, next_item.episode)
    return render_close_player(request)


@require_http_methods(["GET"])
@ajax_login_required
def reload_player(request):

    if episode_id := request.player.get():
        log = (
            AudioLog.objects.filter(user=request.user, episode=episode_id)
            .select_related("episode", "episode__podcast")
            .first()
        )
        return render_player(request, {"log": log})

    return HttpResponse()


@ratelimit(key="ip", rate="20/m")
@require_http_methods(["POST"])
@ajax_login_required
def player_time_update(request):
    """Update current play time of episode."""

    try:
        if episode_id := request.player.get():

            AudioLog.objects.filter(episode=episode_id, user=request.user).update(
                completed=None,
                updated=timezone.now(),
                is_playing=True,
                current_time=int(request.POST["current_time"]),
            )

        return HttpResponseNoContent()
    except (KeyError, ValueError):
        return HttpResponseBadRequest()


def render_start_player(request, episode):

    QueueItem.objects.filter(user=request.user, episode=episode).delete()

    log, _ = AudioLog.objects.update_or_create(
        episode=episode,
        user=request.user,
        defaults={
            "completed": None,
            "updated": timezone.now(),
            "is_playing": True,
        },
    )

    request.player.set(episode.id)

    return with_hx_trigger(
        render_player(
            request,
            {
                "log": log,
                "episode": episode,
                "autoplay": True,
            },
        ),
        {
            "remove-queue-item": episode.id,
            "play-episode": episode.id,
        },
    )


def render_close_player(request):
    return with_hx_trigger(render_player(request), "close-player")


def render_player(request, extra_context=None):
    return TemplateResponse(request, "episodes/_player.html", extra_context)
