from __future__ import annotations

from django.conf import settings
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from jcasts.episodes.models import Episode, QueueItem
from jcasts.podcasts.models import Podcast
from jcasts.shared.pagination import render_paginated_response


@require_http_methods(["GET"])
def index(request: HttpRequest) -> HttpResponse:

    follows = (
        set(request.user.follow_set.values_list("podcast", flat=True))
        if request.user.is_authenticated
        else set()
    )

    promoted = "promoted" in request.GET

    podcast_qs = Podcast.objects.fresh()

    if follows and not promoted:
        podcast_qs = podcast_qs.filter(pk__in=follows)
    else:
        podcast_qs = podcast_qs.filter(promoted=True)

    episodes = (
        Episode.objects.select_related("podcast")
        .filter(
            podcast__in=set(podcast_qs.values_list("pk", flat=True)),
            pub_date__gte=timezone.now() - settings.FRESHNESS_THRESHOLD,
        )
        .order_by("-pub_date", "-id")
        .distinct()
    )

    return render_episode_list_response(
        request,
        episodes,
        "episodes/index.html",
        {
            "promoted": promoted,
            "has_follows": bool(follows),
            "search_url": reverse("episodes:search_episodes"),
        },
        cached=promoted,
    )


@require_http_methods(["GET"])
def search_episodes(request: HttpRequest) -> HttpResponse:

    if not request.search:
        return redirect("episodes:index")

    episodes = (
        Episode.objects.select_related("podcast")
        .search(request.search.value)
        .order_by("-rank", "-pub_date")
    )

    return render_episode_list_response(
        request, episodes, "episodes/search.html", cached=True
    )


@require_http_methods(["GET"])
def actions(request: HttpRequest, episode_id: int) -> HttpResponse:

    episode = get_episode_or_404(
        request, episode_id, with_podcast=True, with_current_time=True
    )

    is_detail = request.GET.get("detail", False)

    if request.user.is_authenticated:

        is_playing = request.player.has(episode.id)

        is_queue = (
            False
            if is_playing
            else QueueItem.objects.filter(user=request.user).exists()
        )
    else:
        is_playing = False
        is_queue = False

    return TemplateResponse(
        request,
        "episodes/_actions.html",
        {
            "episode": episode,
            "is_favorited": episode.is_favorited(request.user),
            "is_queued": episode.is_queued(request.user),
            "is_detail": is_detail,
            "is_playing": is_playing,
            "is_queue": is_queue,
        },
    )


@require_http_methods(["GET"])
def episode_detail(
    request: HttpRequest, episode_id: int, slug: str | None = None
) -> HttpResponse:
    episode = get_episode_or_404(
        request, episode_id, with_podcast=True, with_current_time=True
    )

    return TemplateResponse(
        request,
        "episodes/detail.html",
        {
            "episode": episode,
            "og_data": episode.get_opengraph_data(request),
            "is_playing": request.player.has(episode.id),
            "next_episode": Episode.objects.get_next_episode(episode),
            "previous_episode": Episode.objects.get_previous_episode(episode),
        },
    )


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


def render_episode_list_response(
    request: HttpRequest,
    episodes: QuerySet,
    template_name: str,
    extra_context: dict | None = None,
    cached: bool = False,
) -> TemplateResponse:
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
