from __future__ import annotations

from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from ratelimit.decorators import ratelimit

from jcasts.common.decorators import ajax_login_required
from jcasts.common.http import HttpResponseConflict, HttpResponseNoContent
from jcasts.common.pagination import pagination_response
from jcasts.episodes.models import AudioLog, Bookmark, Episode
from jcasts.podcasts.models import Podcast


@require_http_methods(["GET"])
def index(request: HttpRequest) -> HttpResponse:

    promoted = "promoted" in request.GET
    since = timezone.now() - timedelta(days=14)

    subscribed = (
        set(request.user.subscription_set.values_list("podcast", flat=True))
        if request.user.is_authenticated
        else set()
    )

    podcasts = Podcast.objects.filter(pub_date__gt=since)

    if subscribed and not promoted:
        podcasts = podcasts.filter(pk__in=subscribed)
    else:
        podcasts = podcasts.filter(promoted=True)

    return pagination_response(
        request,
        Episode.objects.filter(pub_date__gt=since)
        .select_related("podcast")
        .filter(
            podcast__in=set(podcasts.values_list("pk", flat=True)),
        )
        .order_by("-pub_date", "-id")
        .distinct(),
        "episodes/index.html",
        "episodes/includes/pagination.html",
        {
            "promoted": promoted,
            "has_subscriptions": bool(subscribed),
            "search_url": reverse("episodes:search_episodes"),
        },
    )


@require_http_methods(["GET"])
def search_episodes(request: HttpRequest) -> HttpResponse:

    if not request.search:
        return HttpResponseRedirect(reverse("episodes:index"))

    return pagination_response(
        request,
        Episode.objects.select_related("podcast")
        .search(request.search.value)
        .order_by("-rank", "-pub_date"),
        "episodes/search.html",
        "episodes/includes/pagination.html",
    )


@require_http_methods(["GET"])
def episode_detail(
    request: HttpRequest, episode_id: int, slug: str | None = None
) -> HttpResponse:
    episode = get_episode_or_404(
        request, episode_id, with_podcast=True, with_current_time=True
    )
    return TemplateResponse(
        request,
        "episodes/detail.html",
        {
            "episode": episode,
            "is_playing": request.player.has(episode.id),
            "is_bookmarked": episode.is_bookmarked(request.user),
            "og_data": episode.get_opengraph_data(request),
            "next_episode": Episode.objects.get_next_episode(episode),
            "previous_episode": Episode.objects.get_previous_episode(episode),
        },
    )


@require_http_methods(["POST"])
@ajax_login_required
def start_player(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    log, _ = AudioLog.objects.update_or_create(
        episode=episode,
        user=request.user,
        defaults={
            "completed": None,
            "updated": timezone.now(),
        },
    )

    request.player.set(episode.id)

    return render_player_action(
        request,
        episode,
        current_time=log.current_time,
        completed=log.completed,
    )


@require_http_methods(["POST"])
@ajax_login_required
def close_player(request: HttpRequest, mark_complete: bool = False) -> HttpResponse:

    if episode_id := request.player.pop():
        episode = get_episode_or_404(request, episode_id)
        completed: datetime | None = None

        if mark_complete:

            completed = timezone.now()

            AudioLog.objects.filter(user=request.user, episode=episode).update(
                completed=completed,
                updated=completed,
                current_time=0,
            )

        return render_player_action(
            request,
            episode,
            completed=completed,
            is_playing=False,
        )

    return HttpResponse()


@ratelimit(key="ip", rate="20/m")
@require_http_methods(["POST"])
@ajax_login_required
def player_time_update(request: HttpRequest) -> HttpResponse:
    """Update current play time of episode."""

    if episode_id := request.player.get():
        try:

            AudioLog.objects.filter(episode=episode_id, user=request.user).update(
                completed=None,
                updated=timezone.now(),
                current_time=int(request.POST["current_time"]),
            )

        except (KeyError, ValueError):
            return HttpResponseBadRequest()

    return HttpResponseNoContent()


@require_http_methods(["GET"])
@login_required
def history(request: HttpRequest) -> HttpResponse:

    logs = AudioLog.objects.filter(user=request.user).select_related(
        "episode", "episode__podcast"
    )

    newest_first = request.GET.get("ordering", "desc") == "desc"

    return pagination_response(
        request,
        logs.search(request.search.value).order_by("-rank", "-updated")
        if request.search
        else logs.order_by("-updated" if newest_first else "updated"),
        "episodes/history.html",
        "episodes/includes/history.html",
        {
            "newest_first": newest_first,
            "oldest_first": not (newest_first),
        },
    )


@require_http_methods(["POST"])
@ajax_login_required
def mark_complete(request: HttpRequest, episode_id: int) -> HttpResponse:

    episode = get_episode_or_404(request, episode_id)

    now = timezone.now()

    if not request.player.has(episode.id):

        AudioLog.objects.filter(user=request.user, episode=episode).update(
            completed=now, current_time=0
        )

        messages.success(request, "Episode marked complete")

    return render_history_action(
        request,
        episode,
        listened=now,
        completed=now,
    )


@require_http_methods(["DELETE"])
@ajax_login_required
def remove_audio_log(request: HttpRequest, episode_id: int) -> HttpResponse:

    episode = get_episode_or_404(request, episode_id)

    if not request.player.has(episode.id):
        AudioLog.objects.filter(user=request.user, episode=episode).delete()
        messages.info(request, "Removed from History")

    return render_history_action(request, episode)


@require_http_methods(["GET"])
@login_required
def bookmarks(request: HttpRequest) -> HttpResponse:
    bookmarks = Bookmark.objects.filter(user=request.user).select_related(
        "episode", "episode__podcast"
    )
    return pagination_response(
        request,
        bookmarks.search(request.search.value).order_by("-rank", "-created")
        if request.search
        else bookmarks.order_by("-created"),
        "episodes/bookmarks.html",
        "episodes/includes/bookmarks.html",
    )


@require_http_methods(["POST"])
@ajax_login_required
def add_bookmark(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id)

    try:
        Bookmark.objects.create(episode=episode, user=request.user)
    except IntegrityError:
        return HttpResponseConflict()

    messages.success(request, "Added to Bookmarks")
    return render_bookmark_action(request, episode, is_bookmarked=True)


@require_http_methods(["DELETE"])
@ajax_login_required
def remove_bookmark(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id)

    Bookmark.objects.filter(user=request.user, episode=episode).delete()

    messages.info(request, "Removed from Bookmarks")
    return render_bookmark_action(request, episode, is_bookmarked=False)


def get_episode_or_404(
    request: HttpRequest,
    episode_id: int,
    *,
    with_podcast: bool = False,
    with_current_time: bool = False,
) -> Episode:
    qs = Episode.objects.all()
    if with_podcast:
        qs = qs.select_related("podcast")
    if with_current_time:
        qs = qs.with_current_time(request.user)
    return get_object_or_404(qs, pk=episode_id)


def render_player_action(
    request: HttpRequest,
    episode: Episode,
    *,
    is_playing: bool = True,
    completed: datetime | None = None,
    current_time: int | None = None,
):

    return TemplateResponse(
        request,
        "episodes/includes/player.html",
        {
            "episode": episode,
            "current_time": current_time,
            "is_playing": is_playing,
            "completed": completed,
            "listened": timezone.now(),
        },
    )


def render_history_action(
    request: HttpRequest,
    episode: Episode,
    listened: datetime | None = None,
    completed: datetime | None = None,
) -> HttpResponse:
    return TemplateResponse(
        request,
        "episodes/includes/history_toggle.html",
        {
            "episode": episode,
            "listened": listened,
            "completed": completed,
        },
    )


def render_bookmark_action(
    request: HttpRequest, episode: Episode, is_bookmarked: bool
) -> HttpResponse:
    return TemplateResponse(
        request,
        "episodes/includes/bookmark_toggle.html",
        {
            "episode": episode,
            "is_bookmarked": is_bookmarked,
        },
    )
