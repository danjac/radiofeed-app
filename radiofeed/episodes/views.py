# Standard Library
import http
import json

# Django
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

# Third Party Libraries
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from turbo_response import TurboFrame

# Local
from .models import AudioLog, Bookmark, Episode


def episode_list(request):
    """As we have a huge number of episodes, either just show first page
    only unless filtered for search."""
    episodes = (
        Episode.objects.with_current_time(request.user)
        .with_is_bookmarked(request.user)
        .select_related("podcast")
    )
    search = request.GET.get("q", None)
    if search:
        episodes = episodes.search(search).order_by("-rank", "-pub_date")
    else:
        episodes = episodes.subscribed(request.user).order_by("-pub_date")

    return TemplateResponse(
        request, "episodes/index.html", {"episodes": episodes, "search": search},
    )


def episode_detail(request, episode_id, slug=None):
    episode = get_object_or_404(
        Episode.objects.with_current_time(request.user).select_related("podcast"),
        pk=episode_id,
    )
    is_bookmarked = (
        request.user.is_authenticated
        and Bookmark.objects.filter(episode=episode, user=request.user).exists()
    )
    og_data = {
        "url": request.build_absolute_uri(episode.get_absolute_url()),
        "title": f"{request.site.name} | {episode.podcast.title} | {episode.title}",
        "description": episode.description,
        "image": episode.podcast.cover_image.url
        if episode.podcast.cover_image
        else None,
    }

    return TemplateResponse(
        request,
        "episodes/detail.html",
        {"episode": episode, "is_bookmarked": is_bookmarked, "og_data": og_data,},
    )


@login_required
def history(request):
    logs = (
        AudioLog.objects.filter(user=request.user)
        .with_is_bookmarked(request.user)
        .select_related("episode", "episode__podcast")
        .order_by("-updated")
    )

    search = request.GET.get("q", None)
    if search:
        logs = logs.search(search).order_by("-rank", "-updated")
    else:
        logs = logs.order_by("-updated")

    return TemplateResponse(
        request, "episodes/history.html", {"logs": logs, "search": search}
    )


@login_required
def bookmark_list(request):
    bookmarks = (
        Bookmark.objects.filter(user=request.user)
        .with_current_time(request.user)
        .select_related("episode", "episode__podcast")
    )
    search = request.GET.get("q", None)
    if search:
        bookmarks = bookmarks.search(search).order_by("-rank", "-created")
    else:
        bookmarks = bookmarks.order_by("-created")
    return TemplateResponse(
        request, "episodes/bookmarks.html", {"bookmarks": bookmarks, "search": search},
    )


@login_required
@require_POST
def add_bookmark(request, episode_id):
    episode = get_object_or_404(Episode, pk=episode_id)

    try:
        Bookmark.objects.create(episode=episode, user=request.user)
    except IntegrityError:
        pass
    return episode_bookmark_response(request, episode, True)


@login_required
@require_POST
def remove_bookmark(request, episode_id):
    episode = get_object_or_404(Episode, pk=episode_id)
    Bookmark.objects.filter(episode=episode, user=request.user).delete()
    return episode_bookmark_response(request, episode, False)


# Player control views


@require_POST
def toggle_player(request, episode_id):
    """Add episode to session and returns HTML component. The player info
    is then added to the session."""

    episode = get_object_or_404(
        Episode.objects.with_current_time(request.user).select_related("podcast"),
        pk=episode_id,
    )

    player = request.session.pop("player", None)

    if player and request.POST.get("player_action") == "stop":
        send_stop_to_player_channel(request, episode.id)
        response = TurboFrame("player").response()
        response["X-Player-Action"] = "stop"

        return response

    current_time = 0 if episode.completed else episode.current_time or 0

    request.session["player"] = {
        "episode": episode.id,
        "current_time": current_time,
    }

    episode.log_activity(request.user, current_time=current_time)

    if player:
        send_stop_to_player_channel(request, player["episode"])

    send_start_to_player_channel(request, episode.id)

    response = (
        TurboFrame("player")
        .template("episodes/_player.html", {"episode": episode})
        .response(request)
    )
    response["X-Player-Action"] = "play"
    response["X-Player-Episode"] = episode.id
    response["X-Player-Media-Url"] = episode.media_url
    response["X-Player-Current-Time"] = current_time

    return response


@require_POST
def mark_complete(request):
    """Remove player from session when episode has ended."""
    player = request.session.pop("player", None)
    if player:

        episode = get_object_or_404(Episode, pk=player["episode"])
        episode.log_activity(request.user, player["current_time"], completed=True)

        send_stop_to_player_channel(request, episode.id)

        send_sync_current_time_to_player_channel(
            request, episode, current_time=0, completed=True
        )

        return JsonResponse(
            {"autoplay": request.user.is_authenticated and request.user.autoplay}
        )

    return HttpResponseBadRequest("No player loaded")


@require_POST
def sync_player_current_time(request):
    """Update current play time of episode"""

    player = request.session.get("player", None)
    if player:
        episode = get_object_or_404(Episode, pk=player["episode"])
        current_time = get_current_time_from_request(request)
        request.session["player"] = {
            **player,
            "current_time": current_time,
        }
        episode.log_activity(request.user, current_time)
        send_sync_current_time_to_player_channel(
            request, episode, current_time, completed=False
        )
        return HttpResponse(status=http.HTTPStatus.NO_CONTENT)
    return HttpResponseBadRequest()


def get_current_time_from_request(request):
    try:
        return int(json.loads(request.body)["currentTime"])
    except (json.JSONDecodeError, KeyError, ValueError):
        return 0


def episode_bookmark_response(request, episode, is_bookmarked):
    if request.accept_turbo_stream:
        return (
            TurboFrame(f"bookmark-{episode.id}")
            .template(
                "episodes/_bookmark_buttons.html",
                {"episode": episode, "is_bookmarked": is_bookmarked},
            )
            .response(request)
        )
    return redirect(episode.get_absolute_url())


def send_to_player_channel(request, msg_type, data=None):
    data = {
        "type": msg_type,
        "request_id": request.session.session_key,
        **(data or {}),
    }
    async_to_sync(get_channel_layer().group_send)("player", data)


def send_stop_to_player_channel(request, episode_id):
    send_to_player_channel(request, "player.stop", {"episode": episode_id})


def send_start_to_player_channel(request, episode_id):
    send_to_player_channel(request, "player.start", {"episode": episode_id})


def send_sync_current_time_to_player_channel(request, episode, current_time, completed):
    send_to_player_channel(
        request,
        "player.sync_current_time",
        {
            "episode": episode.id,
            "info": {
                "duration": episode.get_duration_in_seconds(),
                "current_time": current_time,
                "completed": completed,
            },
        },
    )
