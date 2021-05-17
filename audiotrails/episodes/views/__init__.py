from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db.models import OuterRef, Subquery
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from audiotrails.podcasts.models import Podcast
from audiotrails.shared.decorators import ajax_login_required
from audiotrails.shared.pagination import render_paginated_response

from ..models import AudioLog, Episode


def index(request: HttpRequest, featured: bool = False) -> HttpResponse:

    # get the latest episode for each podcast

    latest_episodes = (
        Episode.objects.filter(podcast=OuterRef("pk")).order_by("-pub_date").distinct()
    )

    follows = []

    if request.user.is_authenticated:
        follows = list(request.user.follow_set.values_list("podcast", flat=True))

        # filter out any episodes the user has already listened to
        listened_ids = list(
            AudioLog.objects.filter(user=request.user).values_list("episode", flat=True)
        )
        if listened_ids:
            latest_episodes = latest_episodes.exclude(pk__in=listened_ids)

    podcast_ids = (
        list(Podcast.objects.filter(promoted=True).values_list("pk", flat=True))
        if featured or not follows
        else follows
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
            "featured": featured,
            "has_follows": follows,
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
        cached=True,
    )


def preview(request: HttpRequest, episode_id: int) -> HttpResponse:

    episode = get_episode_or_404(
        request, episode_id, with_podcast=True, with_current_time=True
    )

    return TemplateResponse(
        request,
        "episodes/_preview.html",
        {
            "episode": episode,
        },
    )


@ajax_login_required
def actions(request: HttpRequest, episode_id: int) -> HttpResponse:

    episode = get_episode_or_404(
        request, episode_id, with_podcast=True, with_current_time=True
    )

    return TemplateResponse(
        request,
        "episodes/_actions.html",
        {
            "episode": episode,
            "is_favorited": episode.is_favorited(request.user),
            "is_queued": episode.is_queued(request.user),
            "is_playing": request.player.is_playing(episode),
        },
    )


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
            "og_data": episode.get_opengraph_data(request),
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
    episodes: List[Episode],
    template_name: str,
    extra_context: Optional[Dict[str, Any]] = None,
    cached: bool = False,
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
