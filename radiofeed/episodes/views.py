import http
from typing import Literal, TypedDict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import OuterRef, Subquery
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe
from pydantic import BaseModel, ValidationError

from radiofeed.episodes.models import AudioLog, Episode
from radiofeed.http import require_DELETE
from radiofeed.paginator import render_paginated_response
from radiofeed.podcasts.models import Podcast
from radiofeed.request import (
    AuthenticatedHttpRequest,
    HttpRequest,
    is_authenticated_request,
)
from radiofeed.response import (
    HttpResponseConflict,
    HttpResponseNoContent,
    RenderOrRedirectResponse,
)
from radiofeed.search import search_queryset

PlayerAction = Literal["load", "play", "close"]


class PlayerUpdate(BaseModel):
    """Data model for player time update."""

    current_time: int
    duration: int


class PlayerUpdateError(TypedDict):
    """Data model for player error response."""

    error: str


@require_safe
@login_required
def index(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """List latest episodes from subscriptions."""

    latest_episodes = (
        Podcast.objects.subscribed(request.user)
        .annotate(
            latest_episode=Subquery(
                Episode.objects.filter(podcast_id=OuterRef("pk"))
                .order_by("-pub_date", "-pk")
                .values("pk")[:1]
            )
        )
        .filter(latest_episode__isnull=False)
        .order_by("-pub_date")
        .values_list("latest_episode", flat=True)[: settings.DEFAULT_PAGE_SIZE]
    )

    episodes = (
        Episode.objects.filter(pk__in=latest_episodes)
        .select_related("podcast")
        .order_by("-pub_date", "-pk")
    )

    return TemplateResponse(
        request,
        "episodes/index.html",
        {
            "episodes": episodes,
        },
    )


@require_safe
@login_required
def search_episodes(request: HttpRequest) -> RenderOrRedirectResponse:
    """Search any episodes in the database."""

    if request.search:
        episodes = (
            search_queryset(
                Episode.objects.filter(podcast__private=False),
                request.search.value,
                "search_vector",
            )
            .select_related("podcast")
            .order_by("-rank", "-pub_date")
        )

        return render_paginated_response(request, "episodes/search.html", episodes)

    return redirect("episodes:index")


@require_safe
@login_required
def episode_detail(
    request: AuthenticatedHttpRequest,
    episode_id: int,
    slug: str | None = None,
) -> TemplateResponse:
    """Renders episode detail."""
    episode = get_object_or_404(
        Episode.objects.select_related("podcast"),
        pk=episode_id,
    )

    audio_log = request.user.audio_logs.filter(episode=episode).first()

    is_bookmarked = request.user.bookmarks.filter(episode=episode).exists()
    is_playing = request.player.has(episode.pk)

    return TemplateResponse(
        request,
        "episodes/detail.html",
        {
            "episode": episode,
            "audio_log": audio_log,
            "is_bookmarked": is_bookmarked,
            "is_playing": is_playing,
        },
    )


@require_POST
@login_required
def start_player(
    request: AuthenticatedHttpRequest, episode_id: int
) -> TemplateResponse:
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
def close_player(
    request: AuthenticatedHttpRequest,
) -> TemplateResponse | HttpResponseNoContent:
    """Closes audio player."""
    if episode_id := request.player.pop():
        audio_log = get_object_or_404(
            request.user.audio_logs.select_related("episode"),
            episode__pk=episode_id,
        )
        return _render_player_action(request, audio_log, action="close")
    return HttpResponseNoContent()


@require_POST
def player_time_update(request: HttpRequest) -> JsonResponse:
    """Handles player time update AJAX requests."""

    if not is_authenticated_request(request):
        return JsonResponse(
            PlayerUpdateError(error="Authentication required"),
            status=http.HTTPStatus.UNAUTHORIZED,
        )

    episode_id = request.player.get()

    if episode_id is None:
        return JsonResponse(
            PlayerUpdateError(error="No episode in player"),
            status=http.HTTPStatus.BAD_REQUEST,
        )

    try:
        update = PlayerUpdate.model_validate_json(request.body)
    except ValidationError as exc:
        return JsonResponse(
            PlayerUpdateError(error=exc.json()),
            status=http.HTTPStatus.BAD_REQUEST,
        )

    try:
        request.user.audio_logs.update_or_create(
            episode_id=episode_id,
            defaults={
                "listened": timezone.now(),
                "current_time": update.current_time,
                "duration": update.duration,
            },
        )

    except IntegrityError:
        return JsonResponse(
            PlayerUpdateError(error="Update cannot be saved"),
            status=http.HTTPStatus.CONFLICT,
        )

    return JsonResponse(update.model_dump())


@require_safe
@login_required
def history(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """Renders user's listening history. User can also search history."""
    audio_logs = request.user.audio_logs.select_related("episode", "episode__podcast")

    ordering = request.GET.get("order", "desc")
    order_by = "listened" if ordering == "asc" else "-listened"

    if request.search:
        audio_logs = search_queryset(
            audio_logs,
            request.search.value,
            "episode__search_vector",
            "episode__podcast__search_vector",
        ).order_by("-rank", order_by)
    else:
        audio_logs = audio_logs.order_by(order_by)

    return render_paginated_response(
        request,
        "episodes/history.html",
        audio_logs,
        {
            "ordering": ordering,
        },
    )


@require_POST
@login_required
def mark_audio_log_complete(
    request: AuthenticatedHttpRequest, episode_id: int
) -> TemplateResponse:
    """Marks audio log complete."""

    if request.player.has(episode_id):
        raise Http404

    audio_log = get_object_or_404(
        request.user.audio_logs.select_related("episode"),
        episode__pk=episode_id,
    )

    audio_log.current_time = 0
    audio_log.save()

    messages.success(request, "Episode marked complete")

    return _render_audio_log_action(request, audio_log, show_audio_log=True)


@require_DELETE
@login_required
def remove_audio_log(
    request: AuthenticatedHttpRequest, episode_id: int
) -> TemplateResponse:
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

    return _render_audio_log_action(request, audio_log, show_audio_log=False)


@require_safe
@login_required
def bookmarks(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """Renders user's bookmarks. User can also search their bookmarks."""
    bookmarks = request.user.bookmarks.select_related("episode", "episode__podcast")

    ordering = request.GET.get("order", "desc")
    order_by = "created" if ordering == "asc" else "-created"

    if request.search:
        bookmarks = search_queryset(
            bookmarks,
            request.search.value,
            "episode__search_vector",
            "episode__podcast__search_vector",
        ).order_by("-rank", order_by)
    else:
        bookmarks = bookmarks.order_by(order_by)

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
    request: AuthenticatedHttpRequest, episode_id: int
) -> TemplateResponse | HttpResponseConflict:
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
def remove_bookmark(
    request: AuthenticatedHttpRequest, episode_id: int
) -> TemplateResponse:
    """Remove episode from bookmarks."""
    episode = get_object_or_404(Episode, pk=episode_id)
    request.user.bookmarks.filter(episode=episode).delete()

    messages.info(request, "Removed from Bookmarks")

    return _render_bookmark_action(request, episode, is_bookmarked=False)


def _render_player_action(
    request: HttpRequest,
    audio_log: AudioLog,
    *,
    action: PlayerAction,
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
    request: AuthenticatedHttpRequest,
    episode: Episode,
    *,
    is_bookmarked: bool,
) -> TemplateResponse:
    return TemplateResponse(
        request,
        "episodes/detail.html#bookmark_button",
        {
            "episode": episode,
            "is_bookmarked": is_bookmarked,
        },
    )


def _render_audio_log_action(
    request: AuthenticatedHttpRequest,
    audio_log: AudioLog,
    *,
    show_audio_log: bool,
) -> TemplateResponse:
    context = {"episode": audio_log.episode}

    if show_audio_log:
        context["audio_log"] = audio_log

    return TemplateResponse(request, "episodes/detail.html#audio_log", context)
