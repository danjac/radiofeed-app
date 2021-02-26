import http
import json

from typing import Dict, List, Optional

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Max, OuterRef, QuerySet, Subquery
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from turbo_response import Action, TurboFrame, TurboStream, TurboStreamResponse

from radiofeed.pagination import render_paginated_response
from radiofeed.podcasts.models import Podcast
from radiofeed.shortcuts import render_component
from radiofeed.users.decorators import ajax_login_required

from .models import AudioLog, Episode, Favorite, QueueItem


def index(request: HttpRequest) -> HttpResponse:

    podcast_ids: List[int] = []
    show_promotions: bool = False

    if request.user.is_authenticated:
        podcast_ids = list(
            request.user.subscription_set.values_list("podcast", flat=True)
        )

    if not podcast_ids:
        podcast_ids = list(
            Podcast.objects.filter(promoted=True).values_list("pk", flat=True)
        )
        show_promotions = True

    # we want a list of the *latest* episode for each podcast
    latest_episodes = (
        Episode.objects.filter(podcast=OuterRef("pk")).order_by("-pub_date").distinct()
    )

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
        return redirect(
            "episodes:index" if request.user.is_authenticated else "podcasts:index"
        )

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
    episode = get_episode_detail_or_404(request, episode_id)

    if request.turbo.frame:

        return (
            TurboFrame(request.turbo.frame)
            .template(
                "episodes/_preview.html",
                {
                    "episode": episode,
                    "is_favorited": episode.is_favorited(request.user),
                    "is_queued": episode.is_queued(request.user),
                },
            )
            .response(request)
        )

    return redirect(episode.get_absolute_url())


def episode_detail(
    request: HttpRequest, episode_id: int, slug: Optional[str] = None
) -> HttpResponse:
    episode = get_episode_detail_or_404(request, episode_id)

    return TemplateResponse(
        request,
        "episodes/about.html",
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
        AudioLog.objects.filter(user=request.user)
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
@login_required
def remove_history(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(episode_id)

    logs = AudioLog.objects.filter(user=request.user)

    logs.filter(episode=episode).delete()

    if logs.count() == 0:
        return TurboStream("history").replace.response("Your History is now empty.")

    return TurboStream(episode.dom.history_list_item).remove.response()


@login_required
def favorites(request: HttpRequest) -> HttpResponse:
    favorites = Favorite.objects.filter(user=request.user).select_related(
        "episode", "episode__podcast"
    )
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
@login_required
def add_favorite(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(episode_id)

    try:
        Favorite.objects.create(episode=episode, user=request.user)
    except IntegrityError:
        pass
    return render_favorite_response(request, episode, True)


@require_POST
@login_required
def remove_favorite(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(episode_id)

    favorites = Favorite.objects.filter(user=request.user)
    favorites.filter(episode=episode).delete()

    return render_favorite_response(request, episode, False)


@login_required
def queue(request: HttpRequest) -> HttpResponse:
    return TemplateResponse(
        request,
        "episodes/queue.html",
        {"queue_items": get_queue_items(request)},
    )


@require_POST
@login_required
def add_to_queue(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(episode_id)
    position = (
        QueueItem.objects.filter(user=request.user).aggregate(Max("position"))[
            "position__max"
        ]
        or 0
    ) + 1

    try:
        QueueItem.objects.create(user=request.user, episode=episode, position=position)
    except IntegrityError:
        pass

    return render_queue_response(request, episode, True)


@require_POST
@login_required
def remove_from_queue(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(episode_id)
    items = QueueItem.objects.filter(user=request.user)
    items.filter(episode=episode).delete()
    return render_queue_response(request, episode, False)


@require_POST
@ajax_login_required
def move_queue_items(request: HttpRequest) -> HttpResponse:

    qs = QueueItem.objects.filter(user=request.user)
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
@login_required
def start_player(
    request: HttpRequest,
    episode_id: int,
) -> HttpResponse:

    episode = get_episode_detail_or_404(request, episode_id)

    return render_player_response(
        request,
        episode,
        current_time=0 if episode.completed else (episode.current_time or 0),
    )


@require_POST
@login_required
def stop_player(request: HttpRequest) -> HttpResponse:
    return render_player_response(request)


@require_POST
@login_required
def play_next_episode(request: HttpRequest) -> HttpResponse:
    """Marks current episode complete, starts next episode in queue
    or closes player if queue empty."""

    next_item = (
        QueueItem.objects.filter(user=request.user)
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


def get_episode_or_404(episode_id: int) -> Episode:
    return get_object_or_404(Episode, pk=episode_id)


def get_episode_detail_or_404(request: HttpRequest, episode_id: int) -> Episode:
    return get_object_or_404(
        Episode.objects.with_current_time(request.user).select_related("podcast"),
        pk=episode_id,
    )


def get_queue_items(request: HttpRequest) -> QuerySet:
    return (
        QueueItem.objects.filter(user=request.user)
        .select_related("episode", "episode__podcast")
        .order_by("position")
    )


def render_player_toggle(
    request: HttpRequest, episode: Episode, is_playing: bool
) -> str:

    return TurboStream(episode.dom.player_toggle).replace.render(
        render_component(request, "player_toggle", episode, is_playing)
    )


def render_queue_items(request: HttpRequest) -> str:
    return (
        TurboStream("queue")
        .replace.template(
            "episodes/_queue.html",
            {"queue_items": get_queue_items(request)},
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


def render_favorite_response(
    request: HttpRequest, episode: Episode, is_favorited: bool
) -> HttpResponse:

    streams: List[str] = [
        TurboStream(episode.dom.favorite_toggle).replace.render(
            render_component(request, "favorite_toggle", episode, is_favorited)
        )
    ]

    num_favorites = request.user.favorite_set.count()

    if is_favorited:
        streams.append(
            TurboStream("favorites")
            .action(Action.UPDATE if num_favorites == 1 else Action.PREPEND)
            .render(render_component(request, "favorite", episode))
        )
    elif num_favorites == 0:
        streams.append(
            TurboStream("favorites").update.render("You have no more Favorites.")
        )
    else:
        streams.append(TurboStream(episode.dom.favorite_list_item).remove.render())

    return TurboStreamResponse(streams)


def render_queue_response(
    request: HttpRequest, episode: Episode, is_queued: bool
) -> HttpResponse:
    return TurboStreamResponse(
        [
            render_queue_items(request),
            TurboStream(episode.dom.queue_toggle).replace.render(
                render_component(request, "queue_toggle", episode, is_queued)
            ),
        ]
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
    QueueItem.objects.filter(user=request.user, episode=next_episode).delete()

    next_episode.log_activity(request.user, current_time=current_time)

    request.player.start(next_episode, current_time)

    response = TurboStreamResponse(
        streams
        + [
            render_player_toggle(request, next_episode, True),
            render_queue_items(request),
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
