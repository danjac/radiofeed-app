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
    remove_episode_from_player(request.user, mark_complete=False)

    return render_start_player(
        request,
        get_episode_or_404(request, episode_id, with_podcast=True),
    )


@require_http_methods(["POST"])
@ajax_login_required
def close_player(request):
    remove_episode_from_player(request.user, mark_complete=False)

    return render_close_player(request)


@require_http_methods(["POST"])
@ajax_login_required
def play_next_episode(request):
    """Marks current episode complete, starts next episode in queue
    or closes player if queue empty."""
    remove_episode_from_player(request.user, mark_complete=True)

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

    if (
        log := AudioLog.objects.playing(request.user)
        .select_related("episode", "episode__podcast")
        .first()
    ) :
        return render_player(request, {"log": log})

    return HttpResponse()


@ratelimit(key="ip", rate="20/m")
@require_http_methods(["POST"])
@ajax_login_required
def player_time_update(request, episode_id):
    """Update current play time of episode.

    Note that we don't check if the episode is currently playing:
    it's possible that a user may close a running episode in one
    device (or open another episode) while playing on another episode,
    so instead we just ensure the current episode is updated while running
    until the user reloads the player.
    """

    try:

        AudioLog.objects.filter(episode=episode_id).update(
            completed=None,
            updated=timezone.now(),
            current_time=int(request.POST["current_time"]),
        )

        return HttpResponseNoContent()
    except (KeyError, ValueError):
        return HttpResponseBadRequest()


def remove_episode_from_player(user, mark_complete):

    now = timezone.now()

    AudioLog.objects.playing(user).update(
        is_playing=False,
        **{
            "updated": now,
            "completed": now,
            "current_time": 0,
        }
        if mark_complete
        else {},
    )


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
