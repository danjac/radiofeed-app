from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Exists, OuterRef
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe

from listenwave.decorators import htmx_login_required, require_DELETE
from listenwave.episodes.models import Episode
from listenwave.http import HttpResponseConflict, HttpResponseNoContent

_index_url = reverse_lazy("episodes:index")
_search_episodes_url = reverse_lazy("episodes:search_episodes")


@require_safe
@login_required
def index(request: HttpRequest, since: timedelta = timedelta(days=14)) -> HttpResponse:
    """List latest episodes from subscriptions if any, else latest episodes from
    promoted podcasts."""

    # tbd: move search to separate page
    episodes = Episode.objects.select_related("podcast")

    if request.search:
        episodes = (
            episodes.search(request.search.value)
            .filter(podcast__private=False)
            .select_related("podcast")
            .order_by("-rank", "-pub_date")
        )
        cache_episodes = True
    else:
        episodes = episodes.filter(
            pub_date__gt=timezone.now() - timedelta(days=14)
        ).order_by("-pub_date", "-id")

        subscribed_episodes = episodes.annotate(
            is_subscribed=Exists(
                request.user.subscriptions.filter(podcast=OuterRef("podcast"))
            )
        ).filter(is_subscribed=True)

        has_subscriptions = subscribed_episodes.exists()

        episodes = (
            subscribed_episodes
            if has_subscriptions
            else episodes.filter(podcast__promoted=True)
        )

        cache_episodes = not (has_subscriptions)

    return render(
        request,
        "episodes/index.html",
        {
            "episodes": episodes,
            "cache_episodes": cache_episodes,
        },
    )


@require_safe
@login_required
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
        },
    )


@require_POST
@htmx_login_required
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
@htmx_login_required
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
@login_required
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
@login_required
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
@htmx_login_required
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
@login_required
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
@htmx_login_required
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
@htmx_login_required
def remove_bookmark(request: HttpRequest, episode_id: int) -> HttpResponse:
    """Remove episode from bookmarks."""
    episode = get_object_or_404(Episode, pk=episode_id)
    request.user.bookmarks.filter(episode=episode).delete()

    messages.info(request, "Removed from Bookmarks")

    return _render_bookmark_action(request, episode, is_bookmarked=False)


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
