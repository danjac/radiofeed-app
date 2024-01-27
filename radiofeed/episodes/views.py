from datetime import timedelta

from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Exists, OuterRef
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe

from radiofeed.decorators import require_auth, require_DELETE
from radiofeed.episodes.models import AudioLog, Episode
from radiofeed.episodes.templatetags.audio_player import SessionAudioLog
from radiofeed.htmx import render_htmx
from radiofeed.http import HttpResponseConflict, HttpResponseNoContent
from radiofeed.pagination import render_pagination


@require_safe
def index(request: HttpRequest) -> HttpResponse:
    """List latest episodes from subscriptions if any, else latest episodes from
    promoted podcasts."""
    episodes = (
        Episode.objects.filter(pub_date__gt=timezone.now() - timedelta(days=14))
        .select_related("podcast")
        .order_by("-pub_date", "-id")
    )

    if request.user.is_authenticated:
        subscribed = episodes.annotate(
            is_subscribed=Exists(
                request.user.subscriptions.filter(podcast=OuterRef("podcast"))
            )
        ).filter(is_subscribed=True)

        has_subscriptions = subscribed.exists()
        promoted = "promoted" in request.GET or not has_subscriptions

    else:
        has_subscriptions = False
        promoted = True

    episodes = episodes.filter(podcast__promoted=True) if promoted else subscribed

    return render_pagination(
        request,
        episodes,
        "episodes/index.html",
        {
            "promoted": promoted,
            "has_subscriptions": has_subscriptions,
            "search_url": reverse("episodes:search_episodes"),
            "clear_search_url": request.path,
        },
    )


@require_safe
def search_episodes(request: HttpRequest) -> HttpResponse:
    """Search episodes. If search empty redirects to index page."""
    if request.search:
        episodes = (
            Episode.objects.search(request.search.value)
            .filter(podcast__private__isnull=False)
            .select_related("podcast")
            .order_by("-rank", "-pub_date")
        )
        return render_pagination(
            request,
            episodes,
            "episodes/search.html",
            {
                "search_url": request.path,
                "clear_search_url": reverse("episodes:index"),
            },
        )
    return redirect("episodes:index")


@require_safe
def episode_detail(
    request: HttpRequest, episode_id: int, slug: str | None = None
) -> HttpResponse:
    """Renders episode detail."""
    episode = get_object_or_404(
        Episode.objects.select_related("podcast"),
        pk=episode_id,
    )

    context: dict = {
        "audio_log": None,
        "is_playing": request.player.has(episode.pk),
        "is_bookmarked": False,
    }

    if request.user.is_authenticated:
        context = {
            "audio_log": request.user.audio_logs.filter(episode=episode).first(),
            "is_bookmarked": request.user.bookmarks.filter(episode=episode).exists(),
        }
    return _render_episode_detail(request, episode, context)


@require_POST
def start_player(request: HttpRequest, episode_id: int) -> HttpResponse:
    """Starts player. Creates new audio log if required."""
    episode = get_object_or_404(
        Episode.objects.select_related("podcast"),
        pk=episode_id,
    )

    if request.user.is_authenticated:
        audio_log, _ = request.user.audio_logs.update_or_create(
            episode=episode,
            defaults={
                "listened": timezone.now(),
            },
        )
    else:
        audio_log = SessionAudioLog(episode)

    request.player.set(episode.pk)

    return _render_audio_player_button(request, audio_log, is_playing=True)


@require_POST
def close_player(request: HttpRequest) -> HttpResponse:
    """Closes audio player."""
    if episode_id := request.player.pop():
        if request.user.is_authenticated:
            audio_log = get_object_or_404(
                request.user.audio_logs.select_related("episode"),
                episode__pk=episode_id,
            )
        else:
            episode = get_object_or_404(Episode, pk=episode_id)
            audio_log = SessionAudioLog(episode)
        return _render_audio_player_button(request, audio_log, is_playing=False)

    return HttpResponseNoContent()


@require_POST
def player_time_update(request: HttpRequest) -> HttpResponse:
    """Update current play time of episode.

    Time should be passed in POST as `current_time` integer value.

    Returns:
        HTTP BAD REQUEST if missing/invalid `current_time`, otherwise HTTP NO CONTENT.
    """
    if episode_id := request.player.get():
        try:
            current_time = int(request.POST["current_time"])
            if request.user.is_authenticated:
                request.user.audio_logs.update_or_create(
                    episode=get_object_or_404(Episode, pk=episode_id),
                    defaults={
                        "current_time": current_time,
                        "listened": timezone.now(),
                    },
                )
            else:
                request.player.set_current_time(current_time)
        except (KeyError, ValueError):
            return HttpResponseBadRequest()

    return HttpResponseNoContent()


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

    return render_pagination(
        request,
        audio_logs,
        "episodes/history.html",
        {
            "search_url": request.path,
            "clear_search_url": request.path,
        },
    )


@require_DELETE
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
    return _render_episode_detail(request, audio_log.episode, partial="audio_log")


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

    return render_pagination(
        request,
        bookmarks,
        "episodes/bookmarks.html",
        {
            "search_url": request.path,
            "clear_search_url": request.path,
        },
    )


@require_POST
@require_auth
def add_bookmark(request: HttpRequest, episode_id: int) -> HttpResponse:
    """Add episode to bookmarks."""
    episode = get_object_or_404(Episode, pk=episode_id)

    try:
        request.user.bookmarks.create(episode=episode)
    except IntegrityError:
        return HttpResponseConflict()

    messages.success(request, "Added to Bookmarks")

    return _render_bookmark_button(request, episode, is_bookmarked=True)


@require_DELETE
@require_auth
def remove_bookmark(request: HttpRequest, episode_id: int) -> HttpResponse:
    """Remove episode from bookmarks."""
    episode = get_object_or_404(Episode, pk=episode_id)
    request.user.bookmarks.filter(episode=episode).delete()

    messages.info(request, "Removed from Bookmarks")

    return _render_bookmark_button(request, episode, is_bookmarked=False)


def _render_episode_detail(
    request: HttpRequest,
    episode: Episode,
    extra_context: dict | None = None,
    **kwargs,
) -> HttpResponse:
    return render_htmx(
        request,
        "episodes/detail.html",
        {
            "episode": episode,
            **(extra_context or {}),
        },
        **kwargs,
    )


def _render_bookmark_button(
    request: HttpRequest, episode: Episode, *, is_bookmarked: bool
) -> HttpResponse:
    return _render_episode_detail(
        request,
        episode,
        {"is_bookmarked": is_bookmarked},
        partial="bookmark_button",
    )


def _render_audio_player_button(
    request: HttpRequest,
    audio_log: AudioLog | SessionAudioLog,
    *,
    is_playing: bool,
) -> HttpResponse:
    return _render_episode_detail(
        request,
        audio_log.episode,
        {
            "audio_log": audio_log,
            "is_playing": is_playing,
            "start_player": is_playing,
        },
        partial="audio_player_button",
    )
