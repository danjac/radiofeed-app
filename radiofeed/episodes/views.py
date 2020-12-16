# Standard Library
import json

# Django
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

# Local
from .models import Bookmark, Episode, History


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
    qs = Episode.objects.filter(podcast=episode.podcast)

    next_episode = qs.filter(pub_date__gt=episode.pub_date).order_by("pub_date").first()
    prev_episode = (
        qs.filter(pub_date__lt=episode.pub_date).order_by("-pub_date").first()
    )

    return TemplateResponse(
        request,
        "episodes/detail.html",
        {
            "episode": episode,
            "is_bookmarked": is_bookmarked,
            "next_episode": next_episode,
            "prev_episode": prev_episode,
        },
    )


@login_required
def history(request):
    logs = (
        History.objects.filter(user=request.user)
        .select_related("episode", "episode__podcast")
        .order_by("-updated")
    )

    search = request.GET.get("q", None)
    if search:
        logs = logs.search(search).order_by("-rank", "-updated")
    else:
        logs = logs.order_by("-updated")

    return TemplateResponse(request, "episodes/history.html", {"logs": logs})


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
        messages.success(request, "You have bookmarked this episode")
    except IntegrityError:
        pass
    return redirect(episode.get_absolute_url())


@login_required
@require_POST
def remove_bookmark(request, episode_id):
    episode = get_object_or_404(Episode, pk=episode_id)
    Bookmark.objects.filter(episode=episode, user=request.user).delete()
    messages.info(request, "Bookmark has been removed")
    return redirect(episode.get_absolute_url())


# Player control views


@require_POST
def start_player(request, episode_id):
    """Add episode to session"""
    episode = get_object_or_404(
        Episode.objects.select_related("podcast"), pk=episode_id
    )
    try:
        current_time = int(json.loads(request.body)["current_time"])
    except (json.JSONDecodeError, KeyError, ValueError):
        current_time = 0

    request.session["player"] = {
        "episode": episode.id,
        "current_time": 0,
        "paused": False,
    }
    episode.log_activity(request.user, current_time=current_time)
    return TemplateResponse(request, "episodes/_player.html", {"episode": episode})


@require_POST
def toggle_player_pause(request, paused):
    player = request.session.get("player", None)
    if player:
        request.session["player"] = {**player, "paused": paused}
    return HttpResponse(status=204)


@require_POST
def stop_player(request):
    """Remove player from session"""
    player = request.session.pop("player", None)
    if player:
        episode = get_object_or_404(Episode, pk=player["episode"])
        episode.log_activity(
            request.user, player["current_time"],
        )
    return HttpResponse(status=204)


@require_POST
def update_player_time(request):
    """Update current play time of episode"""

    player = request.session.get("player", None)
    if player:
        episode = get_object_or_404(Episode, pk=player["episode"])
        try:
            current_time = int(json.loads(request.body)["current_time"])
        except (json.JSONDecodeError, KeyError, ValueError):
            current_time = 0
        request.session["player"] = {
            **player,
            "current_time": current_time,
            "paused": False,
        }
        episode.log_activity(request.user, current_time)
    # TBD: return JSON with new player state?
    return HttpResponse(status=204)
