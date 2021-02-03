import http
import json
from typing import Dict, List, Optional

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

from turbo_response import TurboFrame, TurboStream, TurboStreamResponse

from radiofeed.pagination import paginate

from .models import AudioLog, Bookmark, Episode


def episode_list(request: HttpRequest) -> HttpResponse:

    subscriptions: List[int] = (
        list(request.user.subscription_set.values_list("podcast", flat=True))
        if request.user.is_authenticated
        else []
    )
    has_subscriptions: bool = bool(subscriptions)

    episodes = Episode.objects.select_related("podcast").distinct()

    if request.search:
        episodes = episodes.search(request.search).order_by("-rank", "-pub_date")
    elif subscriptions:
        episodes = episodes.filter(podcast__in=subscriptions).order_by("-pub_date")
    else:
        episodes = episodes.none()

    context = {
        "page_obj": paginate(request, episodes),
        "has_subscriptions": has_subscriptions,
    }

    if request.turbo.frame:

        return (
            TurboFrame(request.turbo.frame)
            .template("episodes/_episode_list.html", context)
            .response(request)
        )

    return TemplateResponse(request, "episodes/index.html", context)


def episode_detail(
    request: HttpRequest, episode_id: int, slug: Optional[str] = None
) -> HttpResponse:
    episode = get_object_or_404(
        Episode.objects.with_current_time(request.user).select_related("podcast"),
        pk=episode_id,
    )
    return TemplateResponse(
        request,
        "episodes/detail.html",
        {
            "episode": episode,
            "is_bookmarked": is_episode_bookmarked(request, episode),
            "og_data": get_episode_opengraph_data(request, episode),
        },
    )


@login_required
def episode_actions(request: HttpRequest, episode_id: str) -> HttpResponse:
    episode = get_object_or_404(
        Episode.objects.with_current_time(request.user).select_related("podcast"),
        pk=episode_id,
    )

    if request.turbo.frame:
        return (
            TurboFrame(request.turbo.frame)
            .template(
                "episodes/_actions.html",
                {
                    "episode": episode,
                    "player_toggle_id": f"episode-play-actions-toggle-{episode.id}",
                    "is_episode_playing": request.player.is_playing(episode),
                    "is_bookmarked": is_episode_bookmarked(request, episode),
                },
            )
            .response(request)
        )

    return redirect(episode.get_absolute_url())


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

    context = {
        "page_obj": paginate(request, logs),
    }
    if request.turbo.frame:

        return (
            TurboFrame(request.turbo.frame)
            .template("episodes/history/_episode_list.html", context)
            .response(request)
        )

    return TemplateResponse(request, "episodes/history/index.html", context)


@require_POST
@login_required
def remove_history(request: HttpRequest, episode_id: int) -> HttpResponse:

    episode = get_object_or_404(Episode, pk=episode_id)
    AudioLog.objects.filter(user=request.user, episode=episode).delete()

    if request.turbo:
        return TurboStream(f"episode-{episode.id}").remove.response()
    return redirect("episodes:history")


@login_required
def bookmark_list(request: HttpRequest) -> HttpResponse:
    bookmarks = Bookmark.objects.filter(user=request.user).select_related(
        "episode", "episode__podcast"
    )
    if request.search:
        bookmarks = bookmarks.search(request.search).order_by("-rank", "-created")
    else:
        bookmarks = bookmarks.order_by("-created")

    context: Dict = {
        "page_obj": paginate(request, bookmarks),
    }

    if request.turbo.frame:

        return (
            TurboFrame(request.turbo.frame)
            .template("episodes/bookmarks/_episode_list.html", context)
            .response(request)
        )

    return TemplateResponse(request, "episodes/bookmarks/index.html", context)


@require_POST
@login_required
def add_bookmark(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_object_or_404(Episode, pk=episode_id)

    try:
        Bookmark.objects.create(episode=episode, user=request.user)
    except IntegrityError:
        pass
    return episode_bookmark_response(request, episode, True)


@require_POST
@login_required
def remove_bookmark(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_object_or_404(Episode, pk=episode_id)
    Bookmark.objects.filter(user=request.user, episode=episode).delete()
    if "remove" in request.POST:
        return TurboStream(f"episode-{episode.id}").remove.response()
    return episode_bookmark_response(request, episode, False)


# Player control views


@require_POST
def toggle_player(request: HttpRequest, episode_id: int) -> HttpResponse:
    """Add episode to session and returns HTML component. The player info
    is then added to the session."""

    streams: List[str] = []

    # clear session
    if current_episode := request.player.eject():
        streams += render_player_toggles(request, current_episode, False)

        if request.POST.get("mark_complete") == "true":
            current_episode.log_activity(request.user, current_time=0, completed=True)

    if request.POST.get("player_action") == "stop":
        response = TurboStreamResponse(
            streams + [TurboStream("player-controls").remove.render()]
        )
        response["X-Player"] = json.dumps({"action": "stop"})
        return response

    episode = get_object_or_404(
        Episode.objects.with_current_time(request.user).select_related("podcast"),
        pk=episode_id,
    )

    current_time: int = 0 if episode.completed else episode.current_time or 0

    episode.log_activity(request.user, current_time=current_time)

    request.player.start(episode, current_time)

    response = TurboStreamResponse(
        streams
        + render_player_toggles(request, episode, True)
        + [
            TurboStream("player-container")
            .update.template(
                "episodes/player/_player.html", {"episode": episode}, request=request
            )
            .render(),
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


@require_POST
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


def render_player_toggles(
    request: HttpRequest, episode: Episode, is_playing: bool
) -> List[str]:

    return [
        TurboStream(target)
        .replace.template(
            "episodes/player/_toggle.html",
            {
                "episode": episode,
                "is_episode_playing": is_playing,
                "player_toggle_id": target,
            },
            request=request,
        )
        .render()
        for target in [
            f"episode-play-toggle-{episode.id}",
            f"episode-play-actions-toggle-{episode.id}",
        ]
    ]


def episode_bookmark_response(
    request: HttpRequest, episode: Episode, is_bookmarked: bool
) -> HttpResponse:
    if request.turbo:
        # https://github.com/hotwired/turbo/issues/86
        return (
            TurboFrame(episode.get_bookmark_toggle_id())
            .template(
                "episodes/bookmarks/_toggle.html",
                {"episode": episode, "is_bookmarked": is_bookmarked},
            )
            .response(request)
        )
    return redirect(episode)


def get_episode_opengraph_data(
    request: HttpRequest, episode: Episode
) -> Dict[str, str]:
    og_data: Dict = {
        "url": request.build_absolute_uri(episode.get_absolute_url()),
        "title": f"{request.site.name} | {episode.podcast.title} | {episode.title}",
        "description": episode.description,
    }

    if episode.podcast.cover_image:
        og_data |= {
            "image": episode.podcast.cover_image.url,
            "image_height": episode.podcast.cover_image.height,
            "image_width": episode.podcast.cover_image.width,
        }

    return og_data


def is_episode_bookmarked(request: HttpRequest, episode: Episode) -> bool:
    if request.user.is_anonymous:
        return False
    return Bookmark.objects.filter(episode=episode, user=request.user).exists()
