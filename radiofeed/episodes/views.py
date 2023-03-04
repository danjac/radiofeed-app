from __future__ import annotations

import http

from datetime import datetime, timedelta

from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe

from radiofeed.decorators import require_auth
from radiofeed.episodes.models import Episode
from radiofeed.pagination import render_pagination_response


@require_safe
@require_auth
def index(request: HttpRequest) -> HttpResponse:
    """List latest episodes from subscriptions if any, else latest episodes from promoted podcasts."""
    subscribed = set(request.user.subscriptions.values_list("podcast", flat=True))
    promoted = "promoted" in request.GET or not subscribed

    episodes = (
        Episode.objects.filter(pub_date__gt=timezone.now() - timedelta(days=14))
        .select_related("podcast")
        .order_by("-pub_date", "-id")
    )

    if promoted:
        episodes = episodes.filter(podcast__promoted=True)
    else:
        episodes = episodes.filter(podcast__pk__in=subscribed)

    return render_pagination_response(
        request,
        episodes,
        "episodes/index.html",
        "episodes/pagination/episodes.html",
        {
            "promoted": promoted,
            "has_subscriptions": bool(subscribed),
            "search_url": reverse("episodes:search_episodes"),
        },
    )


@require_safe
@require_auth
def search_episodes(request: HttpRequest) -> HttpResponse:
    """Search episodes. If search empty redirects to index page."""
    if request.search:
        return render_pagination_response(
            request,
            (
                Episode.objects.select_related("podcast")
                .search(request.search.value)
                .order_by("-rank", "-pub_date")
            ),
            "episodes/search.html",
            "episodes/pagination/episodes.html",
        )

    return redirect("episodes:index")


@require_safe
@require_auth
def episode_detail(
    request: HttpRequest, episode_id: int, slug: str | None = None
) -> HttpResponse:
    """Renders episode detail."""
    episode = get_object_or_404(
        Episode.objects.select_related("podcast"),
        pk=episode_id,
    )

    context = {
        "episode": episode,
        "is_bookmarked": request.user.bookmarks.filter(episode=episode).exists(),
    }

    if audio_log := request.user.audio_logs.filter(episode=episode).first():
        context = {
            **context,
            "listened": audio_log.listened,
            "current_time": audio_log.current_time,
            "is_playing": audio_log.is_playing,
        }

    return render(request, "episodes/detail.html", context)


@require_POST
@require_auth
def start_player(request: HttpRequest, episode_id: int) -> HttpResponse:
    """Starts player. Creates new audio log if necessary and adds episode to player session tracker."""
    episode = get_object_or_404(
        Episode.objects.select_related("podcast"), pk=episode_id
    )

    # close all other current playing episodes
    request.user.audio_logs.update(is_playing=False)

    audio_log, _ = request.user.audio_logs.update_or_create(
        episode=episode,
        defaults={
            "listened": timezone.now(),
            "is_playing": True,
        },
    )

    return _render_play_toggle(
        request,
        episode,
        start_player=True,
        current_time=audio_log.current_time,
        listened=audio_log.listened,
    )


@require_POST
@require_auth
def close_player(request: HttpRequest) -> HttpResponse:
    """Closes player. Removes episode to player session tracker."""
    if (
        audio_log := request.user.audio_logs.filter(is_playing=True)
        .select_related("episode")
        .first()
    ):
        audio_log.is_playing = False
        audio_log.save()

        return _render_play_toggle(
            request,
            audio_log.episode,
            start_player=False,
            current_time=audio_log.current_time,
            listened=audio_log.listened,
        )

    return HttpResponse()


@require_POST
@require_auth
def player_time_update(request: HttpRequest) -> HttpResponse:
    """Update current play time of episode.

    Time should be passed in POST as `current_time` integer value.

    Returns:
        HTTP BAD REQUEST if missing/invalid `current_time`, otherwise HTTP NO CONTENT.
    """
    try:
        request.user.audio_logs.filter(is_playing=True).update(
            current_time=int(request.POST["current_time"]),
            listened=timezone.now(),
        )

    except (KeyError, ValueError):
        return HttpResponseBadRequest()

    return HttpResponse(status=http.HTTPStatus.NO_CONTENT)


@require_safe
@require_auth
def history(request: HttpRequest) -> HttpResponse:
    """Renders user's listening history. User can also search history."""
    audio_logs = request.user.audio_logs.select_related("episode", "episode__podcast")

    if request.search:
        audio_logs = audio_logs.search(request.search.value).order_by(
            "-rank", "-listened"
        )
    else:
        audio_logs = audio_logs.order_by(
            "-listened" if request.ordering.is_desc else "listened"
        )

    return render_pagination_response(
        request,
        audio_logs,
        "episodes/history.html",
        "episodes/pagination/audio_logs.html",
    )


@require_POST
@require_auth
def remove_audio_log(request: HttpRequest, episode_id: int) -> HttpResponse:
    """Removes audio log from user history and returns HTMX snippet."""
    audio_log = get_object_or_404(
        request.user.audio_logs.select_related("episode"),
        episode__pk=episode_id,
        is_playing=False,
    )

    audio_log.delete()

    messages.info(request, "Removed from History")

    return (
        render(
            request, "episodes/includes/history.html", {"episode": audio_log.episode}
        )
        if request.htmx
        else redirect(audio_log.episode.get_absolute_url())
    )


@require_safe
@require_auth
def bookmarks(request: HttpRequest) -> HttpResponse:
    """Renders user's bookmarks. User can also search their bookmarks."""
    bookmarks = request.user.bookmarks.select_related("episode", "episode__podcast")

    if request.search:
        bookmarks = bookmarks.search(request.search.value).order_by("-rank", "-created")
    else:
        bookmarks = bookmarks.order_by(
            "-created" if request.ordering.is_desc else "created"
        )

    return render_pagination_response(
        request,
        bookmarks,
        "episodes/bookmarks.html",
        "episodes/pagination/bookmarks.html",
    )


@require_POST
@require_auth
def add_bookmark(request: HttpRequest, episode_id: int) -> HttpResponse:
    """Add episode to bookmarks."""
    episode = get_object_or_404(Episode, pk=episode_id)

    try:
        request.user.bookmarks.create(episode=episode)
    except IntegrityError:
        return HttpResponse(status=http.HTTPStatus.CONFLICT)

    messages.success(request, "Added to Bookmarks")
    return _render_bookmark_toggle(request, episode, True)


@require_POST
@require_auth
def remove_bookmark(request: HttpRequest, episode_id: int) -> HttpResponse:
    """Remove episode from bookmarks."""
    episode = get_object_or_404(Episode, pk=episode_id)
    request.user.bookmarks.filter(episode=episode).delete()

    messages.info(request, "Removed from Bookmarks")
    return _render_bookmark_toggle(request, episode, False)


def _render_play_toggle(
    request: HttpRequest,
    episode: Episode,
    *,
    start_player: bool,
    current_time: datetime | None,
    listened: datetime | None,
) -> HttpResponse:
    return render(
        request,
        "episodes/includes/play_toggle.html",
        {
            "episode": episode,
            "start_player": start_player,
            "is_playing": start_player,
            "current_time": current_time,
            "listened": listened,
        },
    )


def _render_bookmark_toggle(
    request: HttpRequest, episode: Episode, is_bookmarked: bool
) -> HttpResponse:
    if request.htmx:
        return render(
            request,
            "episodes/includes/bookmark_toggle.html",
            {
                "episode": episode,
                "is_bookmarked": is_bookmarked,
            },
        )
    return redirect(episode.get_absolute_url())
