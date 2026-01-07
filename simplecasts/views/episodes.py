from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import OuterRef, Subquery
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST, require_safe

from simplecasts.http.decorators import require_DELETE
from simplecasts.http.request import AuthenticatedHttpRequest, HttpRequest
from simplecasts.http.response import HttpResponseConflict, RenderOrRedirectResponse
from simplecasts.models import AudioLog, Episode, Podcast
from simplecasts.views.paginator import render_paginated_response


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
def detail(
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


@require_safe
@login_required
def search_episodes(request: HttpRequest) -> RenderOrRedirectResponse:
    """Search any episodes in the database."""

    if request.search:
        results = (
            (
                Episode.objects.filter(podcast__private=False).search(
                    request.search.value
                )
            )
            .select_related("podcast")
            .order_by("-rank", "-pub_date")
        )

        return render_paginated_response(
            request, "episodes/search_episodes.html", results
        )

    return redirect("episodes:index")


@require_safe
@login_required
def history(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """Renders user's listening history. User can also search history."""
    audio_logs = request.user.audio_logs.select_related("episode", "episode__podcast")

    ordering = request.GET.get("order", "desc")
    order_by = "listened" if ordering == "asc" else "-listened"

    if request.search:
        audio_logs = audio_logs.search(request.search.value).order_by("-rank", order_by)
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
def mark_complete(
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


@require_safe
@login_required
def bookmarks(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """Renders user's bookmarks. User can also search their bookmarks."""
    bookmarks = request.user.bookmarks.select_related("episode", "episode__podcast")

    ordering = request.GET.get("order", "desc")
    order_by = "created" if ordering == "asc" else "-created"

    if request.search:
        bookmarks = bookmarks.search(request.search.value).order_by("-rank", order_by)
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
