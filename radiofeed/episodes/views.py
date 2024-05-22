from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Exists, OuterRef, QuerySet
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe

from radiofeed.decorators import require_auth, require_DELETE
from radiofeed.episodes.models import Episode
from radiofeed.http import HttpResponseConflict, HttpResponseNoContent
from radiofeed.users.models import User

_search_episodes_url = reverse_lazy("episodes:search_episodes")


@require_safe
@require_auth
def subscriptions(request: HttpRequest) -> HttpResponse:
    """List latest episodes from subscriptions if any, else latest episodes from
    promoted podcasts."""
    episodes = _get_latest_episodes() & _get_subscribed_episodes(request.user)

    if not episodes.exists():
        return redirect("episodes:promotions")

    return render(
        request,
        "episodes/subscriptions.html",
        {
            "episodes": episodes,
            "search_episodes_url": _search_episodes_url,
            "cache_timeout": settings.CACHE_TIMEOUT,
        },
    )


@require_safe
@require_auth
def promotions(request: HttpRequest) -> HttpResponse:
    """List latest episodes from subscriptions if any, else latest episodes from
    promoted podcasts."""
    episodes = _get_latest_episodes().filter(podcast__promoted=True)
    has_subscriptions = _get_subscribed_episodes(request.user).exists()

    return render(
        request,
        "episodes/promotions.html",
        {
            "episodes": episodes,
            "has_subscriptions": has_subscriptions,
            "search_episodes_url": _search_episodes_url,
            "cache_timeout": settings.CACHE_TIMEOUT,
        },
    )


@require_safe
@require_auth
def search_episodes(request: HttpRequest) -> HttpResponse:
    """Search episodes. If search empty redirects to index page."""
    if request.search:
        episodes = (
            Episode.objects.search(request.search.value)
            .filter(podcast__private=False)
            .select_related("podcast")
            .order_by("-rank", "-pub_date")
        )
        return render(
            request,
            "episodes/search.html",
            {
                "episodes": episodes,
                "clear_search_url": reverse("episodes:subscriptions"),
                "cache_timeout": settings.CACHE_TIMEOUT,
            },
        )
    return redirect("episodes:subscriptions")


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

    return render(
        request,
        "episodes/detail.html",
        {
            "episode": episode,
            "audio_log": request.user.audio_logs.filter(episode=episode).first(),
            "is_bookmarked": request.user.bookmarks.filter(episode=episode).exists(),
            "is_playing": request.audio_player.has(episode.pk),
            "cache_timeout": settings.CACHE_TIMEOUT,
        },
    )


@require_POST
@require_auth
def start_player(request: HttpRequest, episode_id: int) -> HttpResponse:
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

    request.audio_player.set(episode.pk)

    return render(
        request,
        "episodes/detail.html#audio_player_button",
        {
            "audio_log": audio_log,
            "episode": episode,
            "is_playing": True,
            "start_player": True,
            "current_time": audio_log.current_time,
        },
    )


@require_POST
@require_auth
def close_player(request: HttpRequest) -> HttpResponse:
    """Closes audio player."""
    if episode_id := request.audio_player.pop():
        audio_log = get_object_or_404(
            request.user.audio_logs.select_related("episode"),
            episode__pk=episode_id,
        )
        return render(
            request,
            "episodes/detail.html#audio_player_button",
            {
                "audio_log": audio_log,
                "episode": audio_log.episode,
                "is_playing": False,
            },
        )
    return HttpResponseNoContent()


@require_POST
@require_auth
def player_time_update(
    request: HttpRequest,
) -> HttpResponse:
    """Update current play time of episode.

    Time should be passed in POST as `current_time` integer value.

    Returns:
        HTTP BAD REQUEST if missing/invalid `current_time`, otherwise HTTP NO CONTENT.
    """
    if episode_id := request.audio_player.get():
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


@require_safe
@require_auth
def history(request: HttpRequest) -> HttpResponse:
    """Renders user's listening history. User can also search history."""
    audio_logs = request.user.audio_logs.select_related("episode", "episode__podcast")
    ordering_asc = request.GET.get("order", "desc") == "asc"

    if request.search:
        audio_logs = audio_logs.search(request.search.value).order_by(
            "-rank", "-listened"
        )
    else:
        audio_logs = audio_logs.order_by("listened" if ordering_asc else "-listened")

    return render(
        request,
        "episodes/history.html",
        {
            "audio_logs": audio_logs,
            "ordering_asc": ordering_asc,
        },
    )


@require_DELETE
@require_auth
def remove_audio_log(request: HttpRequest, episode_id: int) -> HttpResponse:
    """Removes audio log from user history and returns HTMX snippet."""
    # cannot remove episode if in player
    if request.audio_player.has(episode_id):
        raise Http404

    audio_log = get_object_or_404(
        request.user.audio_logs.select_related("episode"),
        episode__pk=episode_id,
    )

    audio_log.delete()

    messages.info(request, "Removed from History")

    return render(
        request,
        "episodes/detail.html#audio_log",
        {
            "episode": audio_log.episode,
        },
    )


@require_safe
@require_auth
def bookmarks(request: HttpRequest) -> HttpResponse:
    """Renders user's bookmarks. User can also search their bookmarks."""
    bookmarks = request.user.bookmarks.select_related("episode", "episode__podcast")

    ordering_asc = request.GET.get("order", "desc") == "asc"

    if request.search:
        bookmarks = bookmarks.search(request.search.value).order_by("-rank", "-created")
    else:
        bookmarks = bookmarks.order_by("created" if ordering_asc else "-created")

    return render(
        request,
        "episodes/bookmarks.html",
        {
            "bookmarks": bookmarks,
            "ordering_asc": ordering_asc,
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

    return _render_bookmark_action(request, episode, is_bookmarked=True)


@require_DELETE
@require_auth
def remove_bookmark(request: HttpRequest, episode_id: int) -> HttpResponse:
    """Remove episode from bookmarks."""
    episode = get_object_or_404(Episode, pk=episode_id)
    request.user.bookmarks.filter(episode=episode).delete()

    messages.info(request, "Removed from Bookmarks")

    return _render_bookmark_action(request, episode, is_bookmarked=False)


def _get_latest_episodes(since=timedelta(days=14)) -> QuerySet[Episode]:
    return (
        Episode.objects.filter(pub_date__gt=timezone.now() - since)
        .select_related("podcast")
        .order_by("-pub_date", "-id")
    )


def _get_subscribed_episodes(user: User) -> QuerySet[Episode]:
    return Episode.objects.annotate(
        is_subscribed=Exists(user.subscriptions.filter(podcast=OuterRef("podcast")))
    ).filter(is_subscribed=True)


def _render_bookmark_action(
    request: HttpRequest, episode: Episode, *, is_bookmarked: bool
) -> HttpResponse:
    return render(
        request,
        "episodes/detail.html#bookmark_button",
        {
            "episode": episode,
            "is_bookmarked": is_bookmarked,
        },
    )
