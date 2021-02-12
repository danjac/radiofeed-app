from typing import Dict, Optional

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse

from radiofeed.pagination import render_paginated_response

from ..models import Podcast, Recommendation
from . import get_podcast_or_404


def podcast_detail(
    request: HttpRequest, podcast_id: int, slug: Optional[str] = None
) -> HttpResponse:
    podcast = get_podcast_or_404(podcast_id)

    total_episodes: int = podcast.episode_set.count()

    return render_podcast_detail_response(
        request,
        "podcasts/detail/detail.html",
        podcast,
        {"total_episodes": total_episodes},
    )


def podcast_recommendations(
    request: HttpRequest, podcast_id: int, slug: Optional[str] = None
) -> HttpResponse:

    podcast = get_podcast_or_404(podcast_id)

    recommendations = (
        Recommendation.objects.filter(podcast=podcast)
        .select_related("recommended")
        .order_by("-similarity", "-frequency")
    )[:12]

    return render_podcast_detail_response(
        request,
        "podcasts/detail/recommendations.html",
        podcast,
        {
            "recommendations": recommendations,
        },
    )


def podcast_episodes(
    request: HttpRequest, podcast_id: int, slug: Optional[str] = None
) -> HttpResponse:

    podcast = get_podcast_or_404(podcast_id)
    ordering: Optional[str] = request.GET.get("ordering")

    if request.turbo.frame:

        # thumbnail will be same for all episodes, so just preload
        # it once here

        episodes = podcast.episode_set.select_related("podcast")

        if request.search:
            episodes = episodes.search(request.search).order_by("-rank", "-pub_date")
        else:
            order_by = "pub_date" if ordering == "asc" else "-pub_date"
            episodes = episodes.order_by(order_by)

        return render_paginated_response(
            request,
            episodes,
            "episodes/_episode_list_cached.html",
            {
                "cache_timeout": settings.DEFAULT_CACHE_TIMEOUT,
                "podcast_image": podcast.get_cover_image_thumbnail(),
                "podcast_url": reverse(
                    "podcasts:podcast_detail", args=[podcast.id, podcast.slug]
                ),
            },
        )

    return render_podcast_detail_response(
        request,
        "podcasts/detail/episodes.html",
        podcast,
        {
            "ordering": ordering,
        },
    )


def get_podcast_detail_context(
    request: HttpRequest,
    podcast: Podcast,
    extra_context: Optional[Dict] = None,
) -> Dict:

    return {
        "podcast": podcast,
        "has_recommendations": Recommendation.objects.filter(podcast=podcast).exists(),
        "is_subscribed": podcast.is_subscribed(request.user),
        "og_data": podcast.get_opengraph_data(request),
    } | (extra_context or {})


def render_podcast_detail_response(
    request: HttpRequest,
    template_name: str,
    podcast: Podcast,
    extra_context: Optional[Dict] = None,
) -> HttpResponse:

    return TemplateResponse(
        request,
        template_name,
        get_podcast_detail_context(request, podcast, extra_context),
    )
