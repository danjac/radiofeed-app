# Standard Library
import http
import json

# Django
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

# Third Party Libraries
from turbo_response import TurboFrame, TurboStream

# RadioFeed
from radiofeed.pagination import paginate

# Local
from .models import AudioLog, Bookmark, Episode


def episode_list(request):

    subscriptions = (
        list(request.user.subscription_set.values_list("podcast", flat=True))
        if request.user.is_authenticated
        else []
    )
    has_subscriptions = bool(subscriptions)

    if request.turbo.frame:

        episodes = Episode.objects.with_current_time(request.user).select_related(
            "podcast"
        )
        if request.search:
            episodes = episodes.search(request.search).order_by("-rank", "-pub_date")
        elif subscriptions:
            episodes = episodes.filter(podcast__in=subscriptions).order_by("-pub_date")[
                : settings.DEFAULT_PAGE_SIZE
            ]
        else:
            episodes = episodes.none()
        return (
            TurboFrame(request.turbo.frame)
            .template(
                "episodes/_index.html",
                {"page_obj": paginate(request, episodes)},
            )
            .response(request)
        )

    return TemplateResponse(
        request,
        "episodes/index.html",
        {
            "has_subscriptions": has_subscriptions,
        },
    )


def episode_detail(request, episode_id, slug=None):
    episode = get_object_or_404(
        Episode.objects.with_current_time(request.user).select_related("podcast"),
        pk=episode_id,
    )
    is_bookmarked = (
        request.user.is_authenticated
        and Bookmark.objects.filter(episode=episode, user=request.user).exists()
    )
    og_data = {
        "url": request.build_absolute_uri(episode.get_absolute_url()),
        "title": f"{request.site.name} | {episode.podcast.title} | {episode.title}",
        "description": episode.description,
        "image": episode.podcast.cover_image.url
        if episode.podcast.cover_image
        else None,
    }

    return TemplateResponse(
        request,
        "episodes/detail.html",
        {
            "episode": episode,
            "is_bookmarked": is_bookmarked,
            "og_data": og_data,
        },
    )


@login_required
def history(request):

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

        return (
            TurboFrame(request.turbo.frame)
            .template(
                "episodes/_history.html",
                {
                    "page_obj": paginate(request, logs),
                },
            )
            .response(request)
        )

    return TemplateResponse(
        request,
        "episodes/history.html",
    )


@require_POST
@login_required
def remove_history(request, episode_id):

    episode = get_object_or_404(Episode, pk=episode_id)

    logs = AudioLog.objects.filter(user=request.user)
    logs.filter(episode=episode).delete()

    if logs.exists() and request.turbo:
        return TurboStream(f"episode-{episode.id}").remove.response()
    messages.info(request, "All done!")
    return redirect("episodes:history")


@login_required
def bookmark_list(request):
    if request.turbo.frame:

        bookmarks = (
            Bookmark.objects.filter(user=request.user)
            .with_current_time(request.user)
            .select_related("episode", "episode__podcast")
        )
        if request.search:
            bookmarks = bookmarks.search(request.search).order_by("-rank", "-created")
        else:
            bookmarks = bookmarks.order_by("-created")

        return (
            TurboFrame(request.turbo.frame)
            .template(
                "episodes/_bookmarks.html",
                {
                    "page_obj": paginate(request, bookmarks),
                },
            )
            .response(request)
        )

    return TemplateResponse(
        request,
        "episodes/bookmarks.html",
    )


@require_POST
@login_required
def add_bookmark(request, episode_id):
    episode = get_object_or_404(Episode, pk=episode_id)

    try:
        Bookmark.objects.create(episode=episode, user=request.user)
    except IntegrityError:
        pass
    return episode_bookmark_response(request, episode, True)


@require_POST
@login_required
def remove_bookmark(request, episode_id):
    episode = get_object_or_404(Episode, pk=episode_id)
    qs = Bookmark.objects.filter(user=request.user)
    qs.filter(episode=episode).delete()

    if "remove" in request.POST:
        if qs.exists():
            return TurboStream(f"episode-{episode.id}").remove.response()

        messages.info(request, "All done!")
        return redirect("episodes:bookmark_list")

    return episode_bookmark_response(request, episode, False)


# Player control views


@require_POST
def toggle_player(request, episode_id):
    """Add episode to session and returns HTML component. The player info
    is then added to the session."""

    # clear session
    request.player.eject()

    if request.POST.get("player_action") == "stop":
        response = TurboFrame("player").response()
        response["X-Player"] = json.dumps({"episode": episode_id, "action": "stop"})
        return response

    episode = get_object_or_404(
        Episode.objects.with_current_time(request.user).select_related("podcast"),
        pk=episode_id,
    )

    current_time = 0 if episode.completed else episode.current_time or 0

    episode.log_activity(request.user, current_time=current_time)

    request.player.start(episode, current_time)

    response = (
        TurboFrame("player")
        .template("episodes/_player.html", {"episode": episode})
        .response(request)
    )
    response["X-Player"] = json.dumps(
        {
            "episode": episode.id,
            "action": "start",
            "mediaUrl": episode.media_url,
            "currentTime": current_time,
        }
    )
    return response


@require_POST
def mark_complete(request):

    if episode := request.player.eject():
        episode.log_activity(request.user, current_time=0, completed=True)
        return HttpResponse(status=http.HTTPStatus.NO_CONTENT)

    return HttpResponseBadRequest("No player loaded")


@require_POST
def player_timeupdate(request):
    """Update current play time of episode"""
    if episode := request.player.get_episode():
        try:
            current_time = int(json.loads(request.body)["currentTime"])
        except (json.JSONDecodeError, KeyError, ValueError):
            return HttpResponseBadRequest("currentTime not provided")

        episode.log_activity(request.user, current_time)
        request.player.set_current_time(current_time)

        return HttpResponse(status=http.HTTPStatus.NO_CONTENT)
    return HttpResponseBadRequest("No player loaded")


def episode_bookmark_response(request, episode, is_bookmarked):
    if request.turbo.frame:
        return (
            TurboFrame(request.turbo.frame)
            .template(
                "episodes/_bookmark_buttons.html",
                {"episode": episode, "is_bookmarked": is_bookmarked},
            )
            .response(request)
        )
    return redirect(episode)
