from datetime import timedelta
from typing import Literal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import (
    Http404,
    HttpRequest,
    HttpResponseBadRequest,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe

from radiofeed.episodes.models import AudioLog, Episode
from radiofeed.http import (
    HttpResponseConflict,
    HttpResponseNoContent,
    HttpResponseUnauthorized,
    require_DELETE,
)
from radiofeed.paginator import render_paginated_response


@require_safe
@login_required
def index(request: HttpRequest) -> TemplateResponse:
    """List latest episodes from subscriptions."""

    episodes = (
        Episode.objects.subscribed(request.user)
        .filter(
            pub_date__gt=timezone.now() - timedelta(days=14),
        )
        .select_related("podcast")
        .order_by("-pub_date", "-id")
    ).distinct()

    return render_paginated_response(request, "episodes/index.html", episodes)


@require_safe
@login_required
def search_episodes(
    request: HttpRequest,
) -> HttpResponseRedirect | TemplateResponse:
    """Search any episodes in the database."""

    if request.search:
        episodes = (
            Episode.objects.search(request.search.value)
            .filter(podcast__private=False)
            .select_related("podcast")
            .order_by("-rank", "-pub_date")
        )

        return render_paginated_response(request, "episodes/search.html", episodes)

    return HttpResponseRedirect(reverse("episodes:index"))


@require_safe
@login_required
def episode_detail(
    request: HttpRequest, episode_id: int, slug: str | None = None
) -> TemplateResponse:
    """Renders episode detail."""
    episode = get_object_or_404(
        Episode.objects.select_related("podcast"),
        pk=episode_id,
    )

    return TemplateResponse(
        request,
        "episodes/detail.html",
        {
            "episode": episode,
            "audio_log": request.user.audio_logs.filter(episode=episode).first(),
            "is_bookmarked": request.user.bookmarks.filter(episode=episode).exists(),
            "is_playing": request.player.has(episode.pk),
        },
    )


@require_POST
@login_required
def start_player(request: HttpRequest, episode_id: int) -> TemplateResponse:
    """Starts player. Creates new audio log if required."""
    episode = get_object_or_404(
        Episode.objects.select_related("podcast"),
        pk=episode_id,
    )

    audio_log, _ = request.user.audio_logs.update_or_create(
        episode=episode,
        defaults={
            "listened": timezone.now(),
        },
    )

    request.player.set(episode.pk)

    return _render_player_action(request, audio_log, action="play")


@require_POST
@login_required
def close_player(request: HttpRequest) -> HttpResponseNoContent | TemplateResponse:
    """Closes audio player."""
    if episode_id := request.player.pop():
        audio_log = get_object_or_404(
            request.user.audio_logs.select_related("episode"),
            episode__pk=episode_id,
        )
        return _render_player_action(request, audio_log, action="close")
    return HttpResponseNoContent()


@require_POST
def player_time_update(
    request: HttpRequest,
) -> HttpResponseBadRequest | HttpResponseNoContent | HttpResponseUnauthorized:
    """Update current play time of episode.

    Time should be passed in POST as `current_time` integer value.

    Returns:
        HTTP BAD REQUEST if missing/invalid `current_time`, otherwise HTTP NO CONTENT.
    """
    if request.user.is_authenticated:
        if episode_id := request.player.get():
            try:
                request.user.audio_logs.update_or_create(
                    episode=get_object_or_404(Episode, pk=episode_id),
                    defaults={
                        "current_time": int(request.POST["current_time"]),
                        "listened": timezone.now(),
                    },
                )
            except (KeyError, ValueError):
                return HttpResponseBadRequest()

        return HttpResponseNoContent()
    return HttpResponseUnauthorized()


@require_safe
@login_required
def history(request: HttpRequest) -> TemplateResponse:
    """Renders user's listening history. User can also search history."""
    audio_logs = request.user.audio_logs.select_related("episode", "episode__podcast")
    ordering = request.GET.get("order", "desc")

    audio_logs = (
        audio_logs.search(request.search.value).order_by("-rank", "-listened")
        if request.search
        else audio_logs.order_by("listened" if ordering == "asc" else "-listened")
    )

    return render_paginated_response(
        request,
        "episodes/history.html",
        audio_logs,
        {
            "ordering": ordering,
        },
    )


@require_DELETE
@login_required
def remove_audio_log(request: HttpRequest, episode_id: int) -> TemplateResponse:
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

    return TemplateResponse(
        request,
        "episodes/detail.html#audio_log",
        {
            "episode": audio_log.episode,
        },
    )


@require_safe
@login_required
def bookmarks(request: HttpRequest) -> TemplateResponse:
    """Renders user's bookmarks. User can also search their bookmarks."""
    bookmarks = request.user.bookmarks.select_related("episode", "episode__podcast")

    ordering = request.GET.get("order", "desc")

    bookmarks = (
        bookmarks.search(request.search.value).order_by("-rank", "-created")
        if request.search
        else bookmarks.order_by("created" if ordering == "asc" else "-created")
    )

    return render_paginated_response(
        request,
        "episodes/bookmarks.html",
        bookmarks,
        {
            "ordering": ordering,
        },
    )


@require_POST
@login_required
def add_bookmark(
    request: HttpRequest, episode_id: int
) -> HttpResponseConflict | TemplateResponse:
    """Add episode to bookmarks."""
    episode = get_object_or_404(Episode, pk=episode_id)

    try:
        request.user.bookmarks.create(episode=episode)
    except IntegrityError:
        return HttpResponseConflict()

    messages.success(request, "Added to Bookmarks")

    return _render_bookmark_action(request, episode, is_bookmarked=True)


@require_DELETE
@login_required
def remove_bookmark(request: HttpRequest, episode_id: int) -> TemplateResponse:
    """Remove episode from bookmarks."""
    episode = get_object_or_404(Episode, pk=episode_id)
    request.user.bookmarks.filter(episode=episode).delete()

    messages.info(request, "Removed from Bookmarks")

    return _render_bookmark_action(request, episode, is_bookmarked=False)


def _render_player_action(
    request: HttpRequest,
    audio_log: AudioLog,
    *,
    action: Literal["play", "close"],
) -> TemplateResponse:
    return TemplateResponse(
        request,
        "episodes/detail.html#audio_player_button",
        {
            "action": action,
            "audio_log": audio_log,
            "episode": audio_log.episode,
            "is_playing": action == "play",
        },
    )


def _render_bookmark_action(
    request: HttpRequest, episode: Episode, *, is_bookmarked: bool
) -> TemplateResponse:
    return TemplateResponse(
        request,
        "episodes/detail.html#bookmark_button",
        {
            "episode": episode,
            "is_bookmarked": is_bookmarked,
        },
    )
