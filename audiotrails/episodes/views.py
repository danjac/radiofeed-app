import http

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from turbo_response import Action, TurboFrame, TurboStream
from turbo_response.decorators import turbo_stream_response

from audiotrails.pagination import render_paginated_response

from .models import AudioLog, Episode, Favorite, QueueItem


def index(request):

    episodes, show_promotions = Episode.objects.latest_episodes(request.user)

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


def search_episodes(request):

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
        cached=True,
    )


def preview(request, episode_id):
    episode = get_episode_or_404(
        request, episode_id, with_podcast=True, with_current_time=True
    )

    return (
        TurboFrame(request.turbo.frame)
        .template(
            "episodes/_preview.html",
            get_episode_detail_context(request, episode),
        )
        .response(request)
        if request.turbo.frame
        else redirect(episode.get_absolute_url())
    )


def episode_detail(request, episode_id, slug=None):
    episode = get_episode_or_404(
        request, episode_id, with_podcast=True, with_current_time=True
    )

    return TemplateResponse(
        request,
        "episodes/detail.html",
        get_episode_detail_context(
            request, episode, {"og_data": episode.get_opengraph_data(request)}
        ),
    )


@login_required
def history(request):

    logs = (
        AudioLog.objects.for_user(request.user)
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
def remove_audio_log(request, episode_id):
    episode = get_episode_or_404(request, episode_id)

    if request.user.is_anonymous:
        return redirect_episode_to_login(episode)

    if AudioLog.objects.delete_log(request.user, episode) == 0:
        return TurboStream("history").replace.response("Your History is now empty.")

    return TurboStream(episode.dom.history).remove.response()


@login_required
def favorites(request):
    favorites = Favorite.objects.for_user(request.user).select_related(
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
@turbo_stream_response
def add_favorite(request, episode_id):
    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    if request.user.is_anonymous:
        return redirect_episode_to_login(episode)

    num_favorites = 0

    try:
        _, num_favorites = Favorite.objects.create_favorite(request.user, episode)
    except IntegrityError:
        pass

    return [
        render_favorite_toggle(request, episode, is_favorited=True),
        TurboStream("favorites")
        .action(Action.UPDATE if num_favorites == 1 else Action.PREPEND)
        .template(
            "episodes/_episode.html",
            {"episode": episode, "dom_id": episode.dom.favorite},
        )
        .render(request=request),
    ]


@require_POST
@turbo_stream_response
def remove_favorite(request, episode_id):
    episode = get_episode_or_404(request, episode_id)

    if request.user.is_anonymous:
        return redirect_episode_to_login(episode)

    num_favorites = Favorite.objects.delete_favorite(request.user, episode)

    return [
        render_favorite_toggle(request, episode, is_favorited=False),
        TurboStream("favorites").update.render("You have no more Favorites.")
        if num_favorites == 0
        else TurboStream(episode.dom.favorite).remove.render(),
    ]


@login_required
def queue(request):
    return TemplateResponse(
        request,
        "episodes/queue.html",
        {
            "queue_items": QueueItem.objects.for_user(request.user)
            .select_related("episode", "episode__podcast")
            .order_by("position")
        },
    )


@require_POST
@turbo_stream_response
def add_to_queue(request, episode_id):

    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    if request.user.is_anonymous:
        return redirect_episode_to_login(episode)

    streams = [
        render_queue_toggle(request, episode, is_queued=True),
    ]

    try:
        new_item, num_items = QueueItem.objects.create_item(request.user, episode)
    except IntegrityError:
        return streams

    return streams + [
        TurboStream("queue")
        .action(Action.UPDATE if num_items == 1 else Action.APPEND)
        .template(
            "episodes/_queue_item.html",
            {
                "episode": episode,
                "item": new_item,
                "dom_id": episode.dom.queue,
            },
        )
        .render(request=request)
    ]


@require_POST
@turbo_stream_response
def remove_from_queue(request, episode_id):
    episode = get_episode_or_404(request, episode_id)

    if request.user.is_anonymous:
        return redirect_episode_to_login(episode)

    has_next = QueueItem.objects.delete_item(request.user, episode)

    return [
        render_queue_toggle(request, episode, is_queued=False),
        render_remove_from_queue(request, episode, has_next),
    ]


@require_POST
def move_queue_items(request):

    if request.user.is_anonymous:
        return HttpResponseForbidden("You must be logged in")

    try:
        QueueItem.objects.move_items(
            request.user, [int(item_id) for item_id in request.POST.getlist("items")]
        )
    except (ValueError):
        return HttpResponseBadRequest("Invalid payload")

    return HttpResponse(status=http.HTTPStatus.NO_CONTENT)


@require_POST
def start_player(
    request,
    episode_id,
):

    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    if request.user.is_anonymous:
        return redirect_episode_to_login(episode)

    return render_player_response(request, episode)


@require_POST
def close_player(request):
    if request.user.is_anonymous:
        return redirect_to_login(settings.HOME_URL)

    return render_player_response(request)


@require_POST
def play_next_episode(request):
    """Marks current episode complete, starts next episode in queue
    or closes player if queue empty."""
    if request.user.is_anonymous:
        return redirect_to_login(settings.HOME_URL)

    if next_item := (
        QueueItem.objects.for_user(request.user)
        .with_current_time(request.user)
        .select_related("episode", "episode__podcast")
        .order_by("position")
        .first()
    ):
        next_episode = next_item.episode
    else:
        next_episode = None

    return render_player_response(request, next_episode, mark_completed=True)


@require_POST
def player_update_current_time(request):
    """Update current play time of episode"""
    if request.player:
        try:
            request.player.current_time = round(float(request.POST["current_time"]))
            return HttpResponse(status=http.HTTPStatus.NO_CONTENT)
        except (KeyError, ValueError):
            pass
    return HttpResponseBadRequest("missing or invalid data")


def get_episode_or_404(
    request,
    episode_id,
    *,
    with_podcast=False,
    with_current_time=False,
):
    qs = Episode.objects.all()
    if with_podcast:
        qs = qs.select_related("podcast")
    if with_current_time:
        qs = qs.with_current_time(request.user)
    return get_object_or_404(qs, pk=episode_id)


def get_episode_detail_context(request, episode, extra_context=None):
    return {
        "episode": episode,
        "is_playing": request.player.is_playing(episode),
        "is_favorited": episode.is_favorited(request.user),
        "is_queued": episode.is_queued(request.user),
        **(extra_context or {}),
    }


def render_queue_toggle(request, episode, is_queued):
    return (
        TurboStream(episode.dom.queue_toggle)
        .replace.template(
            "episodes/_queue_toggle.html",
            {"episode": episode, "is_queued": is_queued},
        )
        .render(request=request)
    )


def render_remove_from_queue(request, episode, has_next):
    if not has_next:
        return TurboStream("queue").update.render(
            "You have no more episodes in your Play Queue"
        )
    return TurboStream(episode.dom.queue).remove.render()


def render_favorite_toggle(request, episode, is_favorited):
    return (
        TurboStream(episode.dom.favorite_toggle)
        .replace.template(
            "episodes/_favorite_toggle.html",
            {"episode": episode, "is_favorited": is_favorited},
        )
        .render(request=request)
    )


def render_player_toggle(request, episode, is_playing):
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


def redirect_episode_to_login(episode):
    return redirect_to_login(episode.get_absolute_url())


def render_episode_list_response(
    request,
    episodes,
    template_name,
    extra_context=None,
    cached=False,
):
    return render_paginated_response(
        request,
        episodes,
        template_name,
        pagination_template_name="episodes/_episodes_cached.html"
        if cached
        else "episodes/_episodes.html",
        extra_context={
            "cache_timeout": settings.DEFAULT_CACHE_TIMEOUT,
            **(extra_context or {}),
        },
    )


def render_player_response(
    request,
    next_episode=None,
    mark_completed=False,
):

    current_episode = request.player.eject(mark_completed=mark_completed)

    if next_episode:
        request.player.start(next_episode)

    return render_player_streams(
        request,
        current_episode,
        next_episode,
        has_next=QueueItem.objects.delete_item(request.user, next_episode)
        if next_episode
        else False,
    )


@turbo_stream_response
def render_player_streams(request, current_episode, next_episode, has_next):

    if request.POST.get("is_modal"):
        yield TurboStream("modal").replace.template("_modal.html").render()

    if current_episode:
        yield render_player_toggle(request, current_episode, False)

    if next_episode:
        yield render_remove_from_queue(request, next_episode, has_next)
        yield render_queue_toggle(request, next_episode, False)
        yield render_player_toggle(request, next_episode, True)

    yield TurboStream("player").replace.template(
        "episodes/_player.html",
        {
            "new_episode": next_episode,
        },
    ).render(request=request)
