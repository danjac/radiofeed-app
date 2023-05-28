import contextlib
import http
from datetime import timedelta

from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Exists, OuterRef, Q
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
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
    """List latest episodes from subscriptions if any, else latest episodes from
    promoted podcasts."""
    subscribed = set(
        request.user.subscriptions.filter(podcast__pub_date__isnull=False).values_list(
            "podcast", flat=True
        )
    )
    promoted = "promoted" in request.GET or not subscribed

    episodes = (
        Episode.objects.filter(pub_date__gt=timezone.now() - timedelta(days=14))
        .select_related("podcast")
        .order_by("-pub_date", "-id")
    )

    if promoted:
        episodes = episodes.filter(
            podcast__promoted=True,
            podcast__private=False,
        )
    else:
        episodes = episodes.filter(podcast__pk__in=subscribed)

    return render_pagination_response(
        request,
        episodes,
        "episodes/index.html",
        "episodes/_episodes.html",
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
                Episode.objects.filter(
                    Q(podcast__private=False)
                    | Q(
                        pk__in=set(
                            request.user.subscriptions.values_list("podcast", flat=True)
                        )
                    )
                )
                .select_related("podcast")
                .search(request.search.value)
                .order_by("-rank", "-pub_date")
            ),
            "episodes/search.html",
            "episodes/_episodes.html",
        )

    return redirect("episodes:index")


@require_safe
@require_auth
def episode_detail(
    request: HttpRequest, episode_id: int, slug: str | None = None
) -> HttpResponse:
    """Renders episode detail."""
    episode = get_object_or_404(
        Episode.objects.annotate(
            is_subscribed=Exists(
                request.user.subscriptions.filter(podcast=OuterRef("podcast"))
            ),
        )
        .filter(Q(podcast__private=False) | Q(is_subscribed=True))
        .select_related("podcast"),
        pk=episode_id,
    )

    return render(
        request,
        "episodes/detail.html",
        {
            "episode": episode,
            "audio_log": request.user.audio_logs.filter(episode=episode).first(),
            "is_bookmarked": request.user.bookmarks.filter(episode=episode).exists(),
            "is_playing": request.player.has(episode.id),
        },
    )


@require_POST
@require_auth
def start_player(request: HttpRequest, episode_id: int) -> HttpResponse:
    """Starts player. Creates new audio log if required."""
    episode = get_object_or_404(
        Episode.objects.annotate(
            is_subscribed=Exists(
                request.user.subscriptions.filter(podcast=OuterRef("podcast"))
            ),
        )
        .filter(Q(podcast__private=False) | Q(is_subscribed=True))
        .select_related("podcast"),
        pk=episode_id,
    )

    audio_log, _ = request.user.audio_logs.update_or_create(
        episode=episode,
        defaults={
            "listened": timezone.now(),
        },
    )

    request.player.set(episode.id)

    return render(
        request,
        "episodes/_player_toggle.html",
        {
            "episode": episode,
            "audio_log": audio_log,
            "is_playing": True,
            "start_player": True,
        },
    )


@require_POST
@require_auth
def close_player(request: HttpRequest) -> HttpResponse:
    """Closes audio player."""
    if episode_id := request.player.pop():
        audio_log = get_object_or_404(
            request.user.audio_logs.select_related("episode"),
            episode__pk=episode_id,
        )
        return render(
            request,
            "episodes/_player_toggle.html",
            {
                "episode": audio_log.episode,
                "audio_log": audio_log,
                "is_playing": False,
            },
        )

    return HttpResponse(status=http.HTTPStatus.NO_CONTENT)


@require_POST
@require_auth
def player_time_update(request: HttpRequest) -> HttpResponse:
    """Update current play time of episode.

    Time should be passed in POST as `current_time` integer value.

    Returns:
        HTTP BAD REQUEST if missing/invalid `current_time`, otherwise HTTP NO CONTENT.
    """
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

    return HttpResponse(status=http.HTTPStatus.NO_CONTENT)


@require_safe
@require_auth
def history(request: HttpRequest) -> HttpResponse:
    """Renders user's listening history. User can also search history."""
    audio_logs = (
        request.user.audio_logs.annotate(
            is_subscribed=Exists(
                request.user.subscriptions.filter(podcast=OuterRef("episode__podcast"))
            )
        )
        .filter(Q(episode__podcast__private=False) | Q(is_subscribed=True))
        .select_related("episode", "episode__podcast")
    )

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
        "episodes/_audio_logs.html",
    )


@require_POST
@require_auth
def remove_audio_log(request: HttpRequest, episode_id: int) -> HttpResponse:
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

    if request.htmx:
        return render(
            request,
            "episodes/_audio_log.html",
            {
                "episode": audio_log.episode,
            },
        )

    return redirect(audio_log.episode.get_absolute_url())


@require_safe
@require_auth
def bookmarks(request: HttpRequest) -> HttpResponse:
    """Renders user's bookmarks. User can also search their bookmarks."""
    bookmarks = (
        request.user.bookmarks.annotate(
            is_subscribed=Exists(
                request.user.subscriptions.filter(podcast=OuterRef("episode__podcast"))
            )
        )
        .filter(Q(episode__podcast__private=False) | Q(is_subscribed=True))
        .select_related("episode", "episode__podcast")
    )

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
        "episodes/_bookmarks.html",
    )


@require_POST
@require_auth
def add_bookmark(request: HttpRequest, episode_id: int) -> HttpResponse:
    """Add episode to bookmarks."""
    episode = get_object_or_404(Episode, pk=episode_id)

    with contextlib.suppress(IntegrityError):
        request.user.bookmarks.create(episode=episode)

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


def _render_bookmark_toggle(
    request: HttpRequest, episode: Episode, is_bookmarked: bool
) -> HttpResponse:
    if request.htmx:
        return render(
            request,
            "episodes/_bookmark_toggle.html",
            {
                "episode": episode,
                "is_bookmarked": is_bookmarked,
            },
        )
    return redirect(episode.get_absolute_url())
