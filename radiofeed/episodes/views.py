# Standard Library
import http
import json

# Django
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

# Local
from .models import AudioLog, Bookmark, Episode
from .utils import format_duration


def episode_list(request):
    episodes = Episode.objects.with_current_time(request.user).select_related("podcast")
    search = request.GET.get("q", None)
    if search:
        episodes = episodes.search(search).order_by("-rank", "-pub_date")
    else:
        episodes = episodes.order_by("-pub_date")

        if request.user.is_authenticated and request.user.subscription_set.exists():
            episodes = episodes.filter(
                podcast__subscription__user=request.user
            ).distinct()

    return TemplateResponse(
        request, "episodes/index.html", {"episodes": episodes, "search": search}
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
        request, "episodes/bookmarks.html", {"bookmarks": bookmarks, "search": search}
    )


@login_required
@require_POST
def add_bookmark(request, episode_id):
    episode = get_object_or_404(Episode, pk=episode_id)

    try:
        Bookmark.objects.create(episode=episode, user=request.user)
    except IntegrityError:
        pass
    return HttpResponse(status=http.HTTPStatus.CREATED)


@login_required
@require_POST
def remove_bookmark(request, episode_id):
    episode = get_object_or_404(Episode, pk=episode_id)
    Bookmark.objects.filter(episode=episode, user=request.user).delete()
    return HttpResponse(status=http.HTTPStatus.NO_CONTENT)


# Player control views


@require_POST
def start_player(request, episode_id):
    """Add episode to session and returns HTML component. The player info
    is then added to the session."""
    episode = get_object_or_404(
        Episode.objects.select_related("podcast"), pk=episode_id
    )

    current_time = get_current_time_from_request(request)

    request.session["player"] = {
        "episode": episode.id,
        "current_time": current_time,
        "paused": False,
    }
    episode.log_activity(request.user, current_time=current_time)
    return TemplateResponse(request, "episodes/_player.html", {"episode": episode})


@require_POST
def toggle_player_pause(request, pause):
    player = request.session.get("player", None)
    if player:
        request.session["player"] = {**player, "paused": pause}
        return JsonResponse({"paused": pause})
    return HttpResponseBadRequest()


@require_POST
def stop_player(request, completed=False):
    """Remove player from session"""
    player = request.session.pop("player", None)
    if player:

        episode = get_object_or_404(Episode, pk=player["episode"])
        episode.log_activity(request.user, player["current_time"], completed)

        extra_context = {"completed": completed}

        next_episode = episode.get_next_episode()
        if next_episode:
            extra_context |= {
                "next_episode": {
                    "episode": next_episode.id,
                    "play_url": reverse(
                        "episodes:start_player", args=[next_episode.id]
                    ),
                    "duration": next_episode.get_duration_in_seconds(),
                }
            }

        return player_status_response(episode, player["current_time"], extra_context)
    return HttpResponseBadRequest()


@require_POST
def update_player_time(request):
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
        return player_status_response(episode, current_time)
    return HttpResponseBadRequest()


def get_current_time_from_request(request):
    try:
        return int(json.loads(request.body)["current_time"])
    except (json.JSONDecodeError, KeyError, ValueError):
        return 0


def player_status_response(episode, current_time, extra_context=None):
    duration = episode.get_duration_in_seconds()
    return JsonResponse(
        {
            "episode": episode.id,
            "current_time": current_time,
            "duration": format_duration(duration),
            "time_remaining": format_duration(duration - current_time),
            "completed": current_time >= duration,
        }
        | (extra_context or {})
    )
