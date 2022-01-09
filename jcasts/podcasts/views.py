from __future__ import annotations

import logging

import requests

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import QuerySet
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from ratelimit.decorators import ratelimit

from jcasts.episodes.models import Episode
from jcasts.episodes.views import render_episode_list
from jcasts.podcasts import itunes
from jcasts.podcasts.models import Category, Podcast, Recommendation, Subscription
from jcasts.shared.decorators import ajax_login_required
from jcasts.shared.paginate import render_paginated_list
from jcasts.shared.response import HttpResponseConflict


@require_http_methods(["GET"])
def index(request: HttpRequest) -> HttpResponse:

    subscribed = (
        set(request.user.subscription_set.values_list("podcast", flat=True))
        if request.user.is_authenticated
        else set()
    )
    podcasts = (
        Podcast.objects.filter(pub_date__isnull=False).order_by("-pub_date").distinct()
    )

    promoted = "promoted" in request.GET or not subscribed

    if promoted:
        podcasts = podcasts.filter(promoted=True)
    else:
        podcasts = podcasts.filter(pk__in=subscribed)

    return render_podcast_list(
        request,
        podcasts,
        "podcasts/index.html",
        {
            "promoted": promoted,
            "show_latest": True,
            "has_subscriptions": bool(subscribed),
            "search_url": reverse("podcasts:search_podcasts"),
        },
        cached=promoted,
    )


@require_http_methods(["GET"])
def search_podcasts(request: HttpRequest) -> HttpResponse:
    if not request.search:
        return HttpResponseRedirect(reverse("podcasts:index"))

    return render_podcast_list(
        request,
        Podcast.objects.filter(pub_date__isnull=False)
        .search(request.search.value)
        .order_by(
            "-rank",
            "-pub_date",
        ),
        "podcasts/search.html",
        cached=True,
    )


@ratelimit(key="ip", rate="20/m")
@require_http_methods(["GET"])
def search_itunes(request: HttpRequest) -> HttpResponse:

    try:
        feeds = itunes.search_cached(request.search.value) if request.search else []
    except requests.RequestException as e:
        logging.exception(e)
        feeds = []

    return TemplateResponse(
        request,
        "podcasts/itunes_search.html",
        {
            "feeds": feeds,
            "clear_search_url": reverse("podcasts:index"),
        },
    )


@require_http_methods(["GET"])
def similar(
    request: HttpRequest,
    podcast_id: int,
    slug: str | None = None,
    limit: int = 12,
) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)

    recommendations = (
        Recommendation.objects.filter(podcast=podcast)
        .select_related("recommended")
        .order_by("-similarity", "-frequency")
    )[:limit]

    return TemplateResponse(
        request,
        "podcasts/similar.html",
        get_podcast_detail_context(
            request,
            podcast,
            {"recommendations": recommendations},
        ),
    )


@require_http_methods(["GET"])
def latest_episode(request: HttpRequest, podcast_id: int) -> HttpResponseRedirect:

    if (
        episode := Episode.objects.filter(podcast=podcast_id)
        .order_by("-pub_date")
        .first()
    ) is None:
        raise Http404()

    return HttpResponseRedirect(episode.get_absolute_url())


@require_http_methods(["GET"])
def podcast_detail(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:
    podcast = get_podcast_or_404(request, podcast_id)

    return TemplateResponse(
        request,
        "podcasts/detail.html",
        get_podcast_detail_context(
            request,
            podcast,
            {
                "subscribed": podcast.is_subscribed(request.user),
            },
        ),
    )


@require_http_methods(["GET"])
def episodes(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)

    newest_first = request.GET.get("ordering", "desc") == "desc"

    episodes = Episode.objects.filter(podcast=podcast).select_related("podcast")

    if request.search:
        episodes = episodes.search(request.search.value).order_by("-rank", "-pub_date")
    else:
        episodes = episodes.order_by("-pub_date" if newest_first else "pub_date")

    return render_episode_list(
        request,
        episodes,
        "podcasts/episodes.html",
        get_podcast_detail_context(
            request,
            podcast,
            {
                "newest_first": newest_first,
                "oldest_first": not (newest_first),
                "is_podcast_detail": True,
            },
        ),
        cached=True,
    )


@require_http_methods(["GET"])
def category_list(request: HttpRequest) -> HttpResponse:

    categories = Category.objects.order_by("name")

    if request.search:
        categories = categories.search(request.search.value)

    return TemplateResponse(
        request, "podcasts/categories.html", {"categories": categories}
    )


@require_http_methods(["GET"])
def category_detail(
    request: HttpRequest, category_id: int, slug: str | None = None
) -> HttpResponse:

    category = get_object_or_404(Category, pk=category_id)
    podcasts = category.podcast_set.filter(pub_date__isnull=False)

    if request.search:
        podcasts = podcasts.search(request.search.value).order_by(
            "-rank",
            "-pub_date",
        )

    else:
        podcasts = podcasts.order_by("-pub_date")

    return render_podcast_list(
        request,
        podcasts,
        "podcasts/category_detail.html",
        {
            "category": category,
            "children": category.children.order_by("name"),
        },
        cached=True,
    )


@require_http_methods(["POST"])
@ajax_login_required
def subscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)

    try:
        Subscription.objects.create(user=request.user, podcast=podcast)
        messages.success(request, "You are now subscribed to this podcast")
        return render_subscribe_action(request, podcast, subscribed=True)
    except IntegrityError:
        return HttpResponseConflict()


@require_http_methods(["POST"])
@ajax_login_required
def unsubscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)

    messages.info(request, "You are no longer subscribed to this podcast")
    Subscription.objects.filter(podcast=podcast, user=request.user).delete()
    return render_subscribe_action(request, podcast, subscribed=False)


def get_podcast_or_404(request: HttpRequest, podcast_id: int) -> Podcast:
    return get_object_or_404(
        Podcast.objects.filter(pub_date__isnull=False), pk=podcast_id
    )


def get_podcast_detail_context(
    request: HttpRequest, podcast: Podcast, extra_context: dict | None = None
) -> dict:

    return {
        "podcast": podcast,
        "num_episodes": Episode.objects.filter(podcast=podcast).count(),
        "has_recommendations": Recommendation.objects.filter(podcast=podcast).exists(),
        "og_data": podcast.get_opengraph_data(request),
    } | (extra_context or {})


def render_subscribe_action(
    request: HttpRequest, podcast: Podcast, subscribed: bool
) -> TemplateResponse:

    return TemplateResponse(
        request,
        "podcasts/_subscribe_action.html",
        {
            "podcast": podcast,
            "subscribed": subscribed,
            "action": True,
        },
    )


def render_podcast_list(
    request: HttpRequest,
    podcasts: QuerySet,
    template_name: str,
    extra_context: dict | None = None,
    cached: bool = False,
) -> TemplateResponse:

    return render_paginated_list(
        request,
        podcasts,
        template_name,
        "podcasts/_podcasts_cached.html" if cached else "podcasts/_podcasts.html",
        {
            "cache_timeout": settings.DEFAULT_CACHE_TIMEOUT,
        }
        | (extra_context or {}),
    )
