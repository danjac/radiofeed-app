from typing import Dict, Optional

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST
from turbo_response import TurboFrame, TurboStream

from radiofeed.episodes.views.list_detail import render_episode_list_response
from radiofeed.shortcuts import render_component

from ..models import Podcast, Recommendation, Subscription


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


def podcast_actions(request: HttpRequest, podcast_id: int) -> HttpResponse:
    podcast = get_podcast_or_404(podcast_id)

    if request.turbo.frame:
        return (
            TurboFrame(request.turbo.frame)
            .template(
                "podcasts/detail/_actions.html",
                {
                    "podcast": podcast,
                    "is_subscribed": podcast.is_subscribed(request.user),
                },
            )
            .response(request)
        )
    return redirect(podcast.get_absolute_url())


@require_POST
@login_required
def subscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:
    podcast = get_podcast_or_404(podcast_id)
    try:
        Subscription.objects.create(user=request.user, podcast=podcast)
    except IntegrityError:
        pass
    return render_subscribe_response(request, podcast, True)


@require_POST
@login_required
def unsubscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:
    podcast = get_podcast_or_404(podcast_id)
    Subscription.objects.filter(podcast=podcast, user=request.user).delete()
    return render_subscribe_response(request, podcast, False)


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


def render_subscribe_response(
    request: HttpRequest, podcast: Podcast, is_subscribed: bool
) -> HttpResponse:

    return TurboStream(podcast.dom.subscribe_toggle).replace.response(
        render_component(request, "subscribe_toggle", podcast, is_subscribed)
    )


def get_podcast_or_404(podcast_id: int) -> Podcast:
    return get_object_or_404(Podcast, pk=podcast_id)
