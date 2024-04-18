from datetime import timedelta

from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Exists, OuterRef
from django.http import (
    Http404,
    HttpRequest,
    HttpResponseBadRequest,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe

from radiofeed.decorators import require_auth, require_DELETE
from radiofeed.episodes.models import Episode
from radiofeed.http import HttpResponseConflict, HttpResponseNoContent

_index_url = reverse_lazy("episodes:index")
_search_episodes_url = reverse_lazy("episodes:search_episodes")


@require_safe
@require_auth
def index(request: HttpRequest) -> TemplateResponse:
    """List latest episodes from subscriptions if any, else latest episodes from
    promoted podcasts."""
    episodes = (
        Episode.objects.filter(pub_date__gt=timezone.now() - timedelta(days=14))
        .select_related("podcast")
        .order_by("-pub_date", "-id")
    )

    subscribed_episodes = episodes.annotate(
        is_subscribed=Exists(
            request.user.subscriptions.filter(podcast=OuterRef("podcast"))
        )
    ).filter(is_subscribed=True)

    has_subscriptions = subscribed_episodes.exists()
    promoted = "promoted" in request.GET or not has_subscriptions

    episodes = (
        episodes.filter(podcast__promoted=True) if promoted else subscribed_episodes
    )

    return TemplateResponse(
        request,
        "episodes/index.html",
        {
            "episodes": episodes,
            "promoted": promoted,
            "has_subscriptions": has_subscriptions,
            "search_episodes_url": _search_episodes_url,
        },
    )


@require_safe
@require_auth
def search_episodes(request: HttpRequest) -> TemplateResponse | HttpResponseRedirect:
    """Search episodes. If search empty redirects to index page."""
    if request.search:
        episodes = (
            Episode.objects.search(request.search.value)
            .filter(podcast__private__isnull=False)
            .select_related("podcast")
            .order_by("-rank", "-pub_date")
        )
        return TemplateResponse(
            request,
            "episodes/search.html",
            {
                "episodes": episodes,
                "clear_search_url": _index_url,
            },
        )
    return HttpResponseRedirect(_index_url)


@require_safe
@require_auth
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
@require_auth
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

    request.player.set(episode.pk, audio_log.current_time)

    return TemplateResponse(
        request,
        "episodes/detail.html#audio_player_button",
        {
            "audio_log": audio_log,
            "episode": episode,
            "is_playing": True,
            "start_player": True,
            "current_time": audio_log.current_time,
            "player_episode": episode,
        },
    )


@require_POST
@require_auth
def close_player(request: HttpRequest) -> TemplateResponse:
    """Closes audio player."""
    if episode_id := request.player.pop():
        audio_log = get_object_or_404(
            request.user.audio_logs.select_related("episode"),
            episode__pk=episode_id,
        )
        return TemplateResponse(
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
) -> HttpResponseBadRequest | HttpResponseNoContent:
    """Update current play time of episode.

    Time should be passed in POST as `current_time` integer value.

    Returns:
        HTTP BAD REQUEST if missing/invalid `current_time`, otherwise HTTP NO CONTENT.
    """
    if episode_id := request.player.get():
        try:
            request.player.current_time = current_time = int(
                request.POST["current_time"]
            )

            request.user.audio_logs.update_or_create(
                episode=get_object_or_404(Episode, pk=episode_id),
                defaults={
                    "current_time": current_time,
                    "listened": timezone.now(),
                },
            )
        except (KeyError, ValueError):
            return HttpResponseBadRequest()

    return HttpResponseNoContent()


@require_safe
@require_auth
def history(request: HttpRequest) -> TemplateResponse:
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

    return TemplateResponse(
        request,
        "episodes/history.html",
        {
            "audio_logs": audio_logs,
        },
    )


@require_DELETE
@require_auth
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
@require_auth
def bookmarks(request: HttpRequest) -> TemplateResponse:
    """Renders user's bookmarks. User can also search their bookmarks."""
    bookmarks = request.user.bookmarks.select_related("episode", "episode__podcast")

    if request.search:
        bookmarks = bookmarks.search(request.search.value).order_by("-rank", "-created")
    else:
        bookmarks = bookmarks.order_by(
            "-created" if request.ordering.is_desc else "created"
        )

    return TemplateResponse(
        request,
        "episodes/bookmarks.html",
        {
            "bookmarks": bookmarks,
        },
    )


@require_POST
@require_auth
def add_bookmark(request: HttpRequest, episode_id: int) -> TemplateResponse:
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
def remove_bookmark(request: HttpRequest, episode_id: int) -> TemplateResponse:
    """Remove episode from bookmarks."""
    episode = get_object_or_404(Episode, pk=episode_id)
    request.user.bookmarks.filter(episode=episode).delete()

    messages.info(request, "Removed from Bookmarks")

    return _render_bookmark_action(request, episode, is_bookmarked=False)


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
