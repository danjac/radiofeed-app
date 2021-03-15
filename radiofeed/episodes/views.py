import http
import json

from typing import Dict, List, Optional

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import F, OuterRef, QuerySet, Subquery
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from turbo_response import Action, TurboFrame, TurboStream, TurboStreamResponse

from radiofeed.pagination import render_paginated_response
from radiofeed.podcasts.models import Podcast
from radiofeed.users.decorators import ajax_login_required

from .models import AudioLog, Episode, Favorite, QueueItem


def index(request: HttpRequest) -> HttpResponse:

    podcast_ids: List[int] = []
    listened_ids: List[int] = []
    show_promotions: bool = False

    if request.user.is_authenticated:
        podcast_ids = list(request.user.follow_set.values_list("podcast", flat=True))
        listened_ids = list(get_audio_logs(request).values_list("episode", flat=True))

    if not podcast_ids:
        podcast_ids = list(
            Podcast.objects.filter(promoted=True).values_list("pk", flat=True)
        )
        show_promotions = True

    # we want a list of the *latest* episode for each podcast
    latest_episodes = (
        Episode.objects.filter(podcast=OuterRef("pk")).order_by("-pub_date").distinct()
    )

    if listened_ids:
        latest_episodes = latest_episodes.exclude(pk__in=listened_ids)

    episode_ids = (
        Podcast.objects.filter(pk__in=podcast_ids)
        .annotate(latest_episode=Subquery(latest_episodes.values("pk")[:1]))
        .values_list("latest_episode", flat=True)
        .distinct()
    )

    episodes = (
        Episode.objects.select_related("podcast")
        .filter(pk__in=set(episode_ids))
        .order_by("-pub_date")
        .distinct()
    )

    return render_episode_list_response(
        request,
        episodes,
        "episodes/index.html",
        {
            "show_promotions": show_promotions,
            "search_url": reverse("episodes:search_episodes"),
        },
        cached=request.user.is_anonymous,
    )


def search_episodes(request: HttpRequest) -> HttpResponse:

    if not request.search:
        return redirect("episodes:index")

    episodes = (
        Episode.objects.select_related("podcast")
        .search(request.search)
        .order_by("-rank", "-pub_date")
    )

    return render_episode_list_response(
        request,
        episodes,
        "episodes/search.html",
        cached=request.user.is_anonymous,
    )


def preview(
    request: HttpRequest,
    episode_id: int,
) -> HttpResponse:
    episode = get_episode_or_404(
        request, episode_id, with_podcast=True, with_current_time=True
    )

    if request.turbo.frame:

        is_favorited = episode.is_favorited(request.user)
        is_queued = episode.is_queued(request.user)

        return (
            TurboFrame(request.turbo.frame)
            .template(
                "episodes/_preview.html",
                {
                    "episode": episode,
                    "is_favorited": is_favorited,
                    "is_queued": is_queued,
                },
            )
            .response(request)
        )

    return redirect(episode.get_absolute_url())


def episode_detail(
    request: HttpRequest, episode_id: int, slug: Optional[str] = None
) -> HttpResponse:
    episode = get_episode_or_404(
        request, episode_id, with_podcast=True, with_current_time=True
    )

    return TemplateResponse(
        request,
        "episodes/detail.html",
        {
            "episode": episode,
            "is_playing": request.player.is_playing(episode),
            "is_favorited": episode.is_favorited(request.user),
            "is_queued": episode.is_queued(request.user),
            "og_data": episode.get_opengraph_data(request),
        },
    )


@login_required
def history(request: HttpRequest) -> HttpResponse:

    logs = (
        get_audio_logs(request)
        .select_related("episode", "episode__podcast")
        .order_by("-updated")
    )

    if request.search:
        logs = logs.search(request.search).order_by("-rank", "-updated")
    else:
        logs = logs.order_by("-updated")

    return render_paginated_response(
        request,
        logs,
        "episodes/history.html",
        "episodes/_history.html",
    )


@require_POST
@ajax_login_required
def remove_audio_log(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id)

    logs = get_audio_logs(request)

    logs.filter(episode=episode).delete()

    if logs.count() == 0:
        return TurboStream("history").replace.response("Your History is now empty.")

    return TurboStream(episode.dom.history).remove.response()


@login_required
def favorites(request: HttpRequest) -> HttpResponse:
    favorites = get_favorites(request).select_related("episode", "episode__podcast")
    if request.search:
        favorites = favorites.search(request.search).order_by("-rank", "-created")
    else:
        favorites = favorites.order_by("-created")

    return render_paginated_response(
        request,
        favorites,
        "episodes/favorites.html",
        "episodes/_favorites.html",
    )


@require_POST
@ajax_login_required
def add_favorite(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    try:
        Favorite.objects.create(episode=episode, user=request.user)
    except IntegrityError:
        pass

    return TurboStreamResponse(
        [
            render_favorite_toggle(request, episode, is_favorited=True),
            TurboStream("favorites")
            .action(
                Action.UPDATE if get_favorites(request).count() == 1 else Action.PREPEND
            )
            .template(
                "episodes/_episode.html",
                {"episode": episode, "dom_id": episode.dom.favorite},
            )
            .render(request=request),
        ]
    )


@require_POST
@ajax_login_required
def remove_favorite(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id)

    favorites = get_favorites(request)

    favorites.filter(episode=episode).delete()

    streams: List[str] = [render_favorite_toggle(request, episode, is_favorited=False)]

    if favorites.count() == 0:
        streams.append(
            TurboStream("favorites").update.render("You have no more Favorites.")
        )
    else:
        streams.append(TurboStream(episode.dom.favorite).remove.render())

    return TurboStreamResponse(streams)


@login_required
def queue(request: HttpRequest) -> HttpResponse:
    return TemplateResponse(
        request,
        "episodes/queue.html",
        {
            "queue_items": get_queue_items(request)
            .select_related("episode", "episode__podcast")
            .order_by("position")
        },
    )


@require_POST
@ajax_login_required
def add_to_queue(request: HttpRequest, episode_id: int) -> HttpResponse:

    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    items = get_queue_items(request)
    items.update(position=F("position") + 1)

    try:
        new_item = QueueItem.objects.create(
            user=request.user, episode=episode, position=1
        )
    except IntegrityError:
        pass

    return TurboStreamResponse(
        [
            render_queue_toggle(request, episode, is_queued=True),
            TurboStream("queue")
            .action(Action.UPDATE if items.count() == 1 else Action.PREPEND)
            .template(
                "episodes/_queue_item.html",
                {"episode": episode, "item": new_item, "dom_id": episode.dom.queue},
            )
            .render(request=request),
        ]
    )


@require_POST
@ajax_login_required
def remove_from_queue(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id)

    items = get_queue_items(request)
    items.filter(episode=episode).delete()

    streams: List[str] = [render_queue_toggle(request, episode, is_queued=False)]

    if items.count() == 0:
        streams.append(
            TurboStream("queue").update.render(
                "You have no more episodes in your Play Queue"
            )
        )
    else:
        streams.append(TurboStream(episode.dom.queue).remove.render())

    return TurboStreamResponse(streams)


@require_POST
@ajax_login_required
def move_queue_items(request: HttpRequest) -> HttpResponse:

    qs = get_queue_items(request)
    items = qs.in_bulk()
    for_update = []

    try:
        for position, item_id in enumerate(request.POST.getlist("items"), 1):
            if item := items[int(item_id)]:
                item.position = position
                for_update.append(item)
    except (KeyError, ValueError):
        return HttpResponseBadRequest("Invalid payload")

    qs.bulk_update(for_update, ["position"])
    return HttpResponse(status=http.HTTPStatus.NO_CONTENT)


@require_POST
@ajax_login_required
def start_player(
    request: HttpRequest,
    episode_id: int,
) -> HttpResponse:

    episode = get_episode_or_404(
        request, episode_id, with_podcast=True, with_current_time=True
    )

    return render_player_response(
        request,
        episode,
        current_time=0 if episode.completed else (episode.current_time or 0),
    )


@require_POST
@ajax_login_required
def stop_player(request: HttpRequest) -> HttpResponse:
    return render_player_response(request)


@require_POST
@ajax_login_required
def play_next_episode(request: HttpRequest) -> HttpResponse:
    """Marks current episode complete, starts next episode in queue
    or closes player if queue empty."""

    next_item = (
        get_queue_items(request)
        .select_related("episode", "episode__podcast")
        .order_by("position")
        .first()
    )

    return render_player_response(
        request,
        next_episode=next_item.episode if next_item else None,
        mark_completed=True,
    )


@require_POST
@ajax_login_required
def player_timeupdate(request: HttpRequest) -> HttpResponse:
    """Update current play time of episode"""

    if episode := request.player.get_episode():
        try:
            current_time = round(float(request.POST["current_time"]))
        except (KeyError, ValueError):
            return HttpResponseBadRequest("current_time missing or invalid")

        try:
            playback_rate = float(request.POST["playback_rate"])
        except (KeyError, ValueError):
            playback_rate = 1.0

        episode.log_activity(request.user, current_time)
        request.player.update(current_time=current_time, playback_rate=playback_rate)

        return HttpResponse(status=http.HTTPStatus.NO_CONTENT)
    return HttpResponseBadRequest("No player loaded")


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


def get_audio_logs(request: HttpRequest) -> QuerySet:
    return AudioLog.objects.filter(user=request.user)


def get_favorites(request: HttpRequest) -> QuerySet:
    return Favorite.objects.filter(user=request.user)


def get_queue_items(request: HttpRequest) -> QuerySet:
    return QueueItem.objects.filter(user=request.user)


def render_queue_toggle(request: HttpRequest, episode: Episode, is_queued: bool) -> str:
    return (
        TurboStream(episode.dom.queue_toggle)
        .replace.template(
            "episodes/_queue_toggle.html", {"episode": episode, "is_queued": is_queued}
        )
        .render(request=request)
    )


def render_favorite_toggle(
    request: HttpRequest, episode: Episode, is_favorited: bool
) -> str:
    return (
        TurboStream(episode.dom.favorite_toggle)
        .replace.template(
            "episodes/_favorite_toggle.html",
            {"episode": episode, "is_favorited": is_favorited},
        )
        .render(request=request)
    )


def render_player_toggle(
    request: HttpRequest, episode: Episode, is_playing: bool
) -> str:

    return (
        TurboStream(episode.dom.player_toggle)
        .replace.template(
            "episodes/_player_toggle.html",
            {
                "episode": episode,
                "is_playing": is_playing,
            },
        )
        .render(request=request)
    )


def render_episode_list_response(
    request: HttpRequest,
    episodes: QuerySet,
    template_name: str,
    extra_context: Optional[Dict] = None,
    cached: bool = False,
) -> HttpResponse:

    extra_context = extra_context or {}

    if cached:
        extra_context["cache_timeout"] = settings.DEFAULT_CACHE_TIMEOUT
        pagination_template_name = "episodes/_episodes_cached.html"
    else:
        pagination_template_name = "episodes/_episodes.html"

    return render_paginated_response(
        request,
        episodes,
        template_name,
        pagination_template_name,
        extra_context,
    )


def render_player_response(
    request: HttpRequest,
    next_episode: Optional[Episode] = None,
    current_time: int = 0,
    mark_completed: bool = False,
) -> HttpResponse:

    streams: List[str] = []

    if current_episode := request.player.eject(mark_completed=mark_completed):
        streams.append(render_player_toggle(request, current_episode, False))

    if next_episode is None:
        response = TurboStreamResponse(
            streams
            + [
                TurboStream("player-controls").remove.render(),
            ]
        )
        response["X-Media-Player"] = json.dumps({"action": "stop"})
        return response

    # remove from queue
    queue_items = get_queue_items(request)
    queue_items.filter(episode=next_episode).delete()

    if queue_items.count() == 0:
        streams.append(TurboStream("queue").replace.render("All done!"))
    else:
        streams.append(TurboStream(next_episode.dom.queue).remove.render())

    next_episode.log_activity(request.user, current_time=current_time)

    request.player.start(next_episode, current_time)

    response = TurboStreamResponse(
        streams
        + [
            render_queue_toggle(request, next_episode, False),
            render_player_toggle(request, next_episode, True),
            TurboStream("player")
            .update.template(
                "episodes/_player_controls.html",
                {
                    "episode": next_episode,
                },
            )
            .render(request=request),
        ]
    )
    response["X-Media-Player"] = json.dumps(
        {
            "action": "start",
            "currentTime": current_time,
            "mediaUrl": next_episode.media_url,
            "metadata": next_episode.get_media_metadata(),
        }
    )
    return response
