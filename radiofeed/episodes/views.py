import http
import json
from typing import Dict, List, Optional, Tuple

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Max, OuterRef, QuerySet, Subquery
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

from turbo_response import TurboFrame, TurboStream, TurboStreamResponse
from turbo_response.stream import TurboStreamTemplate

from radiofeed.pagination import render_paginated_response
from radiofeed.podcasts.models import Podcast
from radiofeed.users.decorators import ajax_login_required

from .models import AudioLog, Episode, Favorite, QueueItem


@login_required
def new_episodes(request: HttpRequest) -> HttpResponse:

    subscriptions: List[int] = (
        list(request.user.subscription_set.values_list("podcast", flat=True))
        if request.user.is_authenticated
        else []
    )
    has_subscriptions: bool = bool(subscriptions)

    if request.turbo.frame:

        if has_subscriptions:
            # we want a list of the *latest* episode for each podcast
            latest_episodes = (
                Episode.objects.filter(podcast=OuterRef("pk"))
                .order_by("-pub_date")
                .distinct()
            )

            episode_ids = (
                Podcast.objects.filter(pk__in=subscriptions)
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
        else:
            episodes = Episode.objects.none()

        return render_episode_list_response(request, episodes)

    return TemplateResponse(
        request,
        "episodes/index.html",
        {
            "has_subscriptions": has_subscriptions,
            "search_url": reverse("episodes:search_episodes"),
        },
    )


def search_episodes(request: HttpRequest) -> HttpResponse:

    if not request.search:
        return redirect(
            "episodes:index" if request.user.is_authenticated else "podcasts:index"
        )

    if request.turbo.frame:
        episodes = (
            Episode.objects.select_related("podcast")
            .search(request.search)
            .order_by("-rank", "-pub_date")
        )
        return render_episode_list_response(request, episodes)

    return TemplateResponse(request, "episodes/search.html")


def episode_detail(
    request: HttpRequest, episode_id: int, slug: Optional[str] = None
) -> HttpResponse:
    episode = get_episode_detail_or_404(request, episode_id)

    return TemplateResponse(
        request,
        "episodes/detail.html",
        {
            "episode": episode,
            "is_favorited": episode.is_favorited(request.user),
            "is_queued": episode.is_queued(request.user),
            "og_data": episode.get_opengraph_data(request),
        },
    )


@login_required
def episode_actions(
    request: HttpRequest,
    episode_id: int,
    actions: Tuple[str, ...] = ("favorite", "queue"),
) -> HttpResponse:
    episode = get_episode_detail_or_404(request, episode_id)

    if request.turbo.frame:
        return (
            TurboFrame(request.turbo.frame)
            .template(
                "episodes/_actions.html",
                {
                    "episode": episode,
                    "actions": actions,
                    "is_favorited": "favorite" in actions
                    and episode.is_favorited(request.user),
                    "is_queued": "queue" in actions and episode.is_queued(request.user),
                },
            )
            .response(request)
        )

    return redirect(episode.get_absolute_url())


@login_required
def history(request: HttpRequest) -> HttpResponse:

    if request.turbo.frame:

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
            request, logs, "episodes/history/_episode_list.html"
        )

    return TemplateResponse(request, "episodes/history/index.html")


@require_POST
@login_required
def remove_history(request: HttpRequest, episode_id: int) -> HttpResponse:

    episode = get_episode_or_404(episode_id)
    AudioLog.objects.filter(user=request.user, episode=episode).delete()

    if request.turbo:
        return TurboStream(f"episode-{episode.id}").remove.response()
    return redirect("episodes:history")


@login_required
def favorites(request: HttpRequest) -> HttpResponse:
    if request.turbo.frame:
        favorites = Favorite.objects.filter(user=request.user).select_related(
            "episode", "episode__podcast"
        )
        if request.search:
            favorites = favorites.search(request.search).order_by("-rank", "-created")
        else:
            favorites = favorites.order_by("-created")

        return render_paginated_response(
            request, favorites, "episodes/favorites/_episode_list.html"
        )

    return TemplateResponse(request, "episodes/favorites/index.html")


@require_POST
@login_required
def add_favorite(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(episode_id)

    try:
        Favorite.objects.create(episode=episode, user=request.user)
    except IntegrityError:
        pass
    return render_episode_favorite_response(request, episode, True)


@require_POST
@login_required
def remove_favorite(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(episode_id)
    Favorite.objects.filter(user=request.user, episode=episode).delete()
    if "remove" in request.POST:
        return TurboStream(f"episode-{episode.id}").remove.response()
    return render_episode_favorite_response(request, episode, False)


# Queue views


@login_required
def queue(request: HttpRequest) -> HttpResponse:
    # we don't want to paginate the queue
    return TemplateResponse(
        request,
        "episodes/queue/index.html",
        {
            "queue_items": QueueItem.objects.filter(user=request.user)
            .select_related("episode", "episode__podcast")
            .order_by("position")
        },
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

    return render_episode_queue_response(request, episode, True)


@require_POST
@login_required
def remove_from_queue(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(episode_id)
    QueueItem.objects.filter(user=request.user, episode=episode).delete()
    if "remove" in request.POST:
        return TurboStreamResponse(render_remove_from_queue_streams(request, episode))
    return render_episode_queue_response(request, episode, False)


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


# Player control views


@require_POST
@login_required
def toggle_player(
    request: HttpRequest,
    episode_id: Optional[int] = None,
    action: str = "play",
) -> HttpResponse:
    """Add episode to session and returns HTML component. The player info
    is then added to the session."""

    streams: List[str] = []

    # clear session
    if current_episode := request.player.eject():
        streams += [render_player_toggle_stream(request, current_episode, False)]

        if request.POST.get("mark_complete") == "true":
            current_episode.log_activity(request.user, current_time=0, completed=True)

    if action == "stop":
        return render_player_stop_response(streams)

    if action == "next":

        if next_item := (
            QueueItem.objects.filter(user=request.user)
            .select_related("episode", "episode__podcast")
            .order_by("position")
            .first()
        ):

            return render_player_start_response(request, next_item.episode, streams)

        # no more items in queue
        return render_player_stop_response(streams)

    # default: start new episode
    if episode_id is None:
        raise Http404()

    episode = get_episode_detail_or_404(request, episode_id)

    current_time = 0 if episode.completed else episode.current_time or 0
    return render_player_start_response(request, episode, streams, current_time)


@require_POST
@ajax_login_required
def player_timeupdate(request: HttpRequest) -> HttpResponse:
    """Update current play time of episode"""

    if episode := request.player.get_episode():
        try:
            current_time = round(float(request.POST["current_time"]))
        except KeyError:
            return HttpResponseBadRequest("current_time not provided")
        except ValueError:
            return HttpResponseBadRequest("current_time invalid")

        try:
            playback_rate = float(request.POST["playback_rate"])
        except (KeyError, ValueError):
            playback_rate = 1.0

        episode.log_activity(request.user, current_time)
        request.player.current_time = current_time
        request.player.playback_rate = playback_rate

        return HttpResponse(status=http.HTTPStatus.NO_CONTENT)
    return HttpResponseBadRequest("No player loaded")


def get_episode_or_404(episode_id: int) -> Episode:
    return get_object_or_404(Episode, pk=episode_id)


def get_episode_detail_or_404(request: HttpRequest, episode_id: int) -> Episode:
    return get_object_or_404(
        Episode.objects.with_current_time(request.user).select_related("podcast"),
        pk=episode_id,
    )


def episode_queue_stream_template(
    episode: Episode, is_queued: bool
) -> TurboStreamTemplate:

    return TurboStream(episode.get_queue_toggle_id()).replace.template(
        "episodes/queue/_toggle.html",
        {"episode": episode, "is_queued": is_queued},
    )


def render_remove_from_queue_streams(
    request: HttpRequest, episode: Episode
) -> List[str]:
    streams = [
        TurboStream(f"queue-item-{episode.id}").remove.render(),
        episode_queue_stream_template(episode, False).render(),
    ]
    if QueueItem.objects.filter(user=request.user).count() == 0:
        streams += [
            TurboStream("queue").append.render("No more items left in queue"),
        ]
    return streams


def render_player_toggle_stream(
    request: HttpRequest, episode: Episode, is_playing: bool
) -> str:

    return (
        TurboStream(episode.get_player_toggle_id())
        .replace.template(
            "episodes/player/_toggle.html",
            {
                "episode": episode,
                "is_episode_playing": is_playing,
            },
            request=request,
        )
        .render()
    )


def render_player_stop_response(streams: List[str]) -> HttpResponse:
    response = TurboStreamResponse(
        streams + [TurboStream("player-controls").remove.render()]
    )
    response["X-Player"] = json.dumps({"action": "stop"})
    return response


def render_player_start_response(
    request: HttpRequest, episode: Episode, streams: List[str], current_time: int = 0
) -> HttpResponse:

    # remove from queue
    QueueItem.objects.filter(user=request.user, episode=episode).delete()

    episode.log_activity(request.user, current_time=current_time)

    request.player.start(episode, current_time)

    response = TurboStreamResponse(
        streams
        + render_remove_from_queue_streams(request, episode)
        + [
            TurboStream("player-container")
            .update.template(
                "episodes/player/_player.html",
                {"episode": episode},
                request=request,
            )
            .render(),
            render_player_toggle_stream(request, episode, True),
        ]
    )
    response["X-Player"] = json.dumps(
        {
            "action": "start",
            "mediaUrl": episode.media_url,
            "currentTime": current_time,
            "metadata": episode.get_media_metadata(),
        }
    )
    return response


def render_episode_favorite_response(
    request: HttpRequest, episode: Episode, is_favorited: bool
) -> HttpResponse:
    if request.turbo:
        return (
            TurboStream(episode.get_favorite_toggle_id())
            .replace.template(
                "episodes/favorites/_toggle.html",
                {"episode": episode, "is_favorited": is_favorited},
            )
            .response(request)
        )
    return redirect(episode)


def render_episode_queue_response(
    request: HttpRequest, episode: Episode, is_queued: bool
) -> HttpResponse:
    if request.turbo:
        return episode_queue_stream_template(episode, is_queued).response(request)
    return redirect(episode)


def render_episode_list_response(
    request: HttpRequest, episodes: QuerySet, extra_context: Optional[Dict] = None
) -> HttpResponse:
    return render_paginated_response(
        request, episodes, "episodes/_episode_list.html", extra_context
    )
