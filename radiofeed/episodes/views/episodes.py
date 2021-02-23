from typing import List, Optional, Tuple

from django.db.models import OuterRef, Subquery
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from turbo_response import TurboFrame

from radiofeed.podcasts.models import Podcast

from ..models import Episode
from . import get_episode_detail_or_404, render_episode_list_response


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
        .order_by("rank", "-pub_date")
    )

    return render_episode_list_response(
        request,
        episodes,
        "episodes/search.html",
        cached=request.user.is_anonymous,
    )


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


def episode_actions(
    request: HttpRequest,
    episode_id: int,
    actions: Tuple[str, ...] = ("favorite", "queue"),
) -> HttpResponse:
    episode = get_episode_detail_or_404(request, episode_id)

    if request.turbo.frame:
        is_favorited = "favorite" in actions and episode.is_favorited(request.user)
        is_queued = "queue" in actions and episode.is_queued(request.user)

        return (
            TurboFrame(request.turbo.frame)
            .template(
                "episodes/_actions.html",
                {
                    "episode": episode,
                    "actions": actions,
                    "is_favorited": is_favorited,
                    "is_queued": is_queued,
                },
            )
            .response(request)
        )

    return redirect(episode.get_absolute_url())
