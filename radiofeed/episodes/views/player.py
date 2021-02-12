import http
import json
from typing import List

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST

from turbo_response import TurboStream, TurboStreamResponse

from radiofeed.users.decorators import ajax_login_required

from ..models import Episode, QueueItem
from . import get_episode_detail_or_404
from .queue import render_remove_from_queue_streams


@require_POST
@login_required
def start_player(
    request: HttpRequest,
    episode_id: int,
) -> HttpResponse:

    episode = get_episode_detail_or_404(request, episode_id)
    current_time = 0 if episode.completed else episode.current_time or 0

    return render_player_start_response(
        request,
        episode,
        [
            render_close_modal(),
            render_player_eject(request),
        ],
        current_time,
    )


@require_POST
@login_required
def stop_player(request: HttpRequest) -> HttpResponse:
    return render_player_stop_response(
        [render_close_modal(), render_player_eject(request)]
    )


@require_POST
@login_required
def play_next_episode(request: HttpRequest) -> HttpResponse:

    streams: List[str] = [render_player_eject(request)]

    if next_item := (
        QueueItem.objects.filter(user=request.user)
        .select_related("episode", "episode__podcast")
        .order_by("position")
        .first()
    ):

        return render_player_start_response(request, next_item.episode, streams)
    return render_player_stop_response(streams)


@require_POST
@ajax_login_required
def player_timeupdate(request: HttpRequest) -> HttpResponse:
    """Update current play time of episode"""

    if episode := request.player.get_episode():
        try:
            current_time = round(float(request.POST["current_time"]))
        except KeyError:
            return HttpResponseBadRequest("current_time not provided")
        except ValueError:
            return HttpResponseBadRequest("current_time invalid")

        try:
            playback_rate = float(request.POST["playback_rate"])
        except (KeyError, ValueError):
            playback_rate = 1.0

        episode.log_activity(request.user, current_time)
        request.player.current_time = current_time
        request.player.playback_rate = playback_rate

        return HttpResponse(status=http.HTTPStatus.NO_CONTENT)
    return HttpResponseBadRequest("No player loaded")


def render_close_modal() -> str:
    return TurboStream("modal").update.render()


def render_player_eject(request: HttpRequest, mark_completed: bool = False) -> str:
    if current_episode := request.player.eject():
        if mark_completed:
            current_episode.log_activity(request.user, current_time=0, completed=True)
        return render_player_toggle_stream(request, current_episode, False)
    return ""


def render_player_toggle_stream(
    request: HttpRequest, episode: Episode, is_playing: bool
) -> str:

    return (
        TurboStream(episode.get_player_toggle_id())
        .replace.template(
            "episodes/player/_toggle.html",
            {
                "episode": episode,
                "is_episode_playing": is_playing,
            },
            request=request,
        )
        .render()
    )


def render_player_stop_response(streams: List[str]) -> HttpResponse:
    response = TurboStreamResponse(
        streams
        + [
            TurboStream("player-controls").remove.render(),
        ]
    )
    response["X-Player"] = json.dumps({"action": "stop"})
    return response


def render_player_start_response(
    request: HttpRequest, episode: Episode, streams: List[str], current_time: int = 0
) -> HttpResponse:

    # remove from queue
    QueueItem.objects.filter(user=request.user, episode=episode).delete()

    episode.log_activity(request.user, current_time=current_time)

    request.player.start(episode, current_time)

    response = TurboStreamResponse(
        streams
        + render_remove_from_queue_streams(request, episode)
        + [
            TurboStream("player-container")
            .update.template(
                "episodes/player/_player.html",
                {"episode": episode},
                request=request,
            )
            .render(),
            render_player_toggle_stream(request, episode, True),
        ]
    )
    response["X-Player"] = json.dumps(
        {
            "action": "start",
            "mediaUrl": episode.media_url,
            "currentTime": current_time,
            "metadata": episode.get_media_metadata(),
        }
    )
    return response
