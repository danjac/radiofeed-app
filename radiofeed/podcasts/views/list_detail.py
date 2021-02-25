from typing import Dict, List, Optional

from django.conf import settings
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page
from turbo_response import TurboFrame

from radiofeed.episodes.views import render_episode_list_response
from radiofeed.pagination import render_paginated_response
from radiofeed.shortcuts import render_component

from .. import itunes
from ..models import Podcast, Recommendation
from ..tasks import sync_podcast_feed


def index(request: HttpRequest) -> HttpResponse:
    subscriptions = (
        list(request.user.subscription_set.values_list("podcast", flat=True))
        if request.user.is_authenticated
        else []
    )
    podcasts = (
        Podcast.objects.filter(pub_date__isnull=False).order_by("-pub_date").distinct()
    )

    if subscriptions:
        podcasts = podcasts.filter(pk__in=subscriptions)
        show_promotions = False
    else:
        podcasts = podcasts.filter(promoted=True)
        show_promotions = True

    return render_podcast_list_response(
        request,
        podcasts,
        "podcasts/list/index.html",
        {
            "show_promotions": show_promotions,
            "search_url": reverse("podcasts:search_podcasts"),
        },
        cached=request.user.is_anonymous,
    )


def search_podcasts(request: HttpRequest) -> HttpResponse:

    if not request.search:
        return redirect("podcasts:index")

    podcasts = (
        Podcast.objects.filter(pub_date__isnull=False)
        .search(request.search)
        .order_by("-rank", "-pub_date")
    )
    return render_podcast_list_response(
        request,
        podcasts,
        "podcasts/list/search.html",
        cached=True,
    )


def search_itunes(request: HttpRequest) -> HttpResponse:

    error: bool = False
    results: itunes.SearchResultList = []
    new_podcasts: List[Podcast] = []

    if request.search:
        try:
            results, new_podcasts = itunes.search_itunes(request.search)
        except (itunes.Timeout, itunes.Invalid):
            error = True

    for podcast in new_podcasts:
        sync_podcast_feed.delay(rss=podcast.rss)

    clear_search_url = f"{reverse('podcasts:index')}?q={request.search}"

    return TemplateResponse(
        request,
        "podcasts/itunes/search.html",
        {
            "results": results,
            "error": error,
            "clear_search_url": clear_search_url,
        },
    )


def about(
    request: HttpRequest, podcast_id: int, slug: Optional[str] = None
) -> HttpResponse:
    podcast = get_podcast_or_404(podcast_id)

    total_episodes: int = podcast.episode_set.count()

    return render_podcast_detail_response(
        request,
        "podcasts/detail/about.html",
        podcast,
        {"total_episodes": total_episodes},
    )


def recommendations(
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


def episodes(
    request: HttpRequest, podcast_id: int, slug: Optional[str] = None
) -> HttpResponse:

    podcast = get_podcast_or_404(podcast_id)
    ordering: Optional[str] = request.GET.get("ordering")

    episodes = podcast.episode_set.select_related("podcast")

    if request.search:
        episodes = episodes.search(request.search).order_by("-rank", "-pub_date")
    else:
        order_by = "pub_date" if ordering == "asc" else "-pub_date"
        episodes = episodes.order_by(order_by)

    return render_episode_list_response(
        request,
        episodes,
        "podcasts/detail/episodes.html",
        {
            **get_podcast_detail_context(request, podcast),
            "ordering": ordering,
            "cover_image": podcast.get_cover_image_thumbnail(),
            "podcast_url": reverse(
                "podcasts:podcast_detail", args=[podcast.id, podcast.slug]
            ),
        },
        cached=request.user.is_anonymous,
    )


@cache_page(60 * 60 * 24)
def podcast_cover_image(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Lazy-loaded podcast image"""
    podcast = get_podcast_or_404(podcast_id)
    return TurboFrame(request.turbo.frame).response(
        render_component(
            request,
            "cover_image",
            podcast,
            lazy=False,
            cover_image=podcast.get_cover_image_thumbnail(),
        )
    )


def get_podcast_or_404(podcast_id: int) -> Podcast:
    return get_object_or_404(Podcast, pk=podcast_id)


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


def render_podcast_list_response(
    request: HttpRequest,
    podcasts: QuerySet,
    template_name: str,
    extra_context: Optional[Dict] = None,
    cached: bool = False,
) -> HttpResponse:

    extra_context = extra_context or {}

    if cached:
        extra_context["cache_timeout"] = settings.DEFAULT_CACHE_TIMEOUT
        partial_template_name = "podcasts/list/_podcast_list_cached.html"
    else:
        partial_template_name = "podcasts/list/_podcast_list.html"

    return render_paginated_response(
        request, podcasts, template_name, partial_template_name, extra_context
    )
