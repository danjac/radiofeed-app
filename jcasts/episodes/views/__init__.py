from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from jcasts.common.paginate import render_paginated_list
from jcasts.episodes.models import Episode
from jcasts.podcasts.models import Podcast


@require_http_methods(["GET"])
def index(request: HttpRequest) -> HttpResponse:

    promoted = "promoted" in request.GET
    since = timezone.now() - timedelta(days=14)

    subscribed = (
        set(request.user.subscription_set.values_list("podcast", flat=True))
        if request.user.is_authenticated
        else set()
    )

    podcast_qs = Podcast.objects.filter(pub_date__gt=since)

    if subscribed and not promoted:
        podcast_qs = podcast_qs.filter(pk__in=subscribed)
    else:
        podcast_qs = podcast_qs.filter(promoted=True)

    episodes = (
        Episode.objects.filter(pub_date__gt=since)
        .select_related("podcast")
        .filter(
            podcast__in=set(podcast_qs.values_list("pk", flat=True)),
        )
        .order_by("-pub_date", "-id")
        .distinct()
    )

    return render_episode_list(
        request,
        episodes,
        "episodes/index.html",
        {
            "promoted": promoted,
            "has_subscriptions": bool(subscribed),
            "search_url": reverse("episodes:search_episodes"),
        },
        cached=promoted,
    )


@require_http_methods(["GET"])
def search_episodes(request: HttpRequest) -> HttpResponse:

    if not request.search:
        return HttpResponseRedirect(reverse("episodes:index"))

    episodes = (
        Episode.objects.select_related("podcast")
        .search(request.search.value)
        .order_by("-rank", "-pub_date")
    )

    return render_episode_list(request, episodes, "episodes/search.html", cached=True)


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
            "is_playing": request.player.has(episode.id),
            "is_bookmarked": episode.is_bookmarked(request.user),
            "og_data": episode.get_opengraph_data(request),
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


def render_episode_list(
    request: HttpRequest,
    episodes: QuerySet,
    template_name: str,
    extra_context: dict | None = None,
    cached: bool = False,
) -> TemplateResponse:
    return render_paginated_list(
        request,
        episodes,
        template_name,
        "episodes/_episodes_cached.html" if cached else "episodes/_episodes.html",
        {
            "cache_timeout": settings.DEFAULT_CACHE_TIMEOUT,
        }
        | (extra_context or {}),
    )
