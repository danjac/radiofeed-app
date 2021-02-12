from typing import List, Optional, Tuple

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from turbo_response import TurboFrame

from radiofeed.pagination import render_paginated_response
from radiofeed.podcasts.models import Podcast

from ..models import Episode
from . import get_episode_detail_or_404


@login_required
def index(request: HttpRequest) -> HttpResponse:

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

        return render_paginated_response(
            request,
            episodes,
            "episodes/_episode_list.html",
        )

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
        return render_paginated_response(
            request,
            episodes,
            "episodes/_episode_list_cached.html",
            {"cache_timeout": settings.DEFAULT_CACHE_TIMEOUT},
        )

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
                    "is_episode_playing": request.player.is_playing(episode),
                    "is_favorited": "favorite" in actions
                    and episode.is_favorited(request.user),
                    "is_queued": "queue" in actions and episode.is_queued(request.user),
                },
            )
            .response(request)
        )

    return redirect(episode.get_absolute_url())
