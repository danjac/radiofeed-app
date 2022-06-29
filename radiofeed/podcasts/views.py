import logging

import requests

from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Exists, OuterRef
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from ratelimit.decorators import ratelimit

from radiofeed.common.decorators import ajax_login_required
from radiofeed.common.http import HttpResponseConflict
from radiofeed.common.pagination import pagination_response
from radiofeed.episodes.models import Episode
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Category, Podcast, Recommendation, Subscription


@require_http_methods(["GET"])
def index(request):

    subscribed = (
        set(request.user.subscription_set.values_list("podcast", flat=True))
        if request.user.is_authenticated
        else set()
    )

    promoted = "promoted" in request.GET or not subscribed

    podcasts = get_podcasts().order_by("-pub_date").distinct()

    podcasts = (
        podcasts.filter(promoted=True)
        if promoted
        else podcasts.filter(pk__in=subscribed)
    )

    return pagination_response(
        request,
        podcasts,
        "podcasts/index.html",
        "podcasts/pagination/podcasts.html",
        {
            "promoted": promoted,
            "has_subscriptions": bool(subscribed),
            "search_url": reverse("podcasts:search_podcasts"),
        },
    )


@require_http_methods(["GET"])
def search_podcasts(request):
    if not request.search:
        return HttpResponseRedirect(reverse("podcasts:index"))

    podcasts = (
        get_podcasts()
        .search(request.search.value)
        .order_by(
            "-rank",
            "-pub_date",
        )
    )

    return pagination_response(
        request,
        podcasts,
        "podcasts/search.html",
        "podcasts/pagination/podcasts.html",
    )


@ratelimit(key="ip", rate="20/m")
@require_http_methods(["GET"])
def search_itunes(request):

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
def latest_episode(request, podcast_id, slug=None):

    if (
        episode := Episode.objects.filter(podcast=podcast_id)
        .order_by("-pub_date")
        .first()
    ) is None:
        raise Http404()

    return HttpResponseRedirect(episode.get_absolute_url())


@require_http_methods(["GET"])
def similar(request, podcast_id, slug=None, limit=12):

    podcast = get_podcast_or_404(podcast_id)

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
def podcast_detail(request, podcast_id, slug=None):
    podcast = get_podcast_or_404(podcast_id)

    return TemplateResponse(
        request,
        "podcasts/detail.html",
        get_podcast_detail_context(
            request,
            podcast,
            {
                "is_subscribed": podcast.is_subscribed(request.user),
            },
        ),
    )


@require_http_methods(["GET"])
def episodes(request, podcast_id, slug=None):

    podcast = get_podcast_or_404(podcast_id)

    newest_first = request.GET.get("ordering", "desc") == "desc"

    episodes = Episode.objects.filter(podcast=podcast).select_related("podcast")

    episodes = (
        episodes.search(request.search.value).order_by("-rank", "-pub_date")
        if request.search
        else episodes.order_by("-pub_date" if newest_first else "pub_date")
    )

    extra_context = {
        "is_podcast_detail": True,
        "newest_first": newest_first,
        "oldest_first": not (newest_first),
    }

    return pagination_response(
        request,
        episodes,
        "podcasts/episodes.html",
        "episodes/pagination/episodes.html",
        extra_context=extra_context
        if request.htmx.target == "object-list"
        else get_podcast_detail_context(request, podcast, extra_context),
    )


@require_http_methods(["GET"])
def category_list(request):

    categories = (
        Category.objects.annotate(
            has_podcasts=Exists(get_podcasts().filter(categories=OuterRef("pk")))
        )
        .filter(has_podcasts=True)
        .order_by("name")
    )

    if request.search:
        categories = categories.search(request.search.value)

    return TemplateResponse(
        request, "podcasts/categories.html", {"categories": categories}
    )


@require_http_methods(["GET"])
def category_detail(request, category_id, slug=None):

    category = get_object_or_404(Category, pk=category_id)
    podcasts = get_podcasts().filter(categories=category).distinct()

    podcasts = (
        podcasts.search(request.search.value).order_by(
            "-rank",
            "-pub_date",
        )
        if request.search
        else podcasts.order_by("-pub_date")
    )

    return pagination_response(
        request,
        podcasts,
        "podcasts/category_detail.html",
        "podcasts/pagination/podcasts.html",
        {"category": category},
    )


@require_http_methods(["POST"])
@ajax_login_required
def subscribe(request, podcast_id):

    podcast = get_podcast_or_404(podcast_id)

    try:
        Subscription.objects.create(user=request.user, podcast=podcast)
    except IntegrityError:
        return HttpResponseConflict()

    messages.success(request, "You are now subscribed to this podcast")
    return subscribe_action_response(request, podcast, True)


@require_http_methods(["DELETE"])
@ajax_login_required
def unsubscribe(request, podcast_id):

    podcast = get_podcast_or_404(podcast_id)

    Subscription.objects.filter(podcast=podcast, user=request.user).delete()

    messages.info(request, "You are no longer subscribed to this podcast")
    return subscribe_action_response(request, podcast, False)


def get_podcasts():
    return Podcast.objects.filter(pub_date__isnull=False)


def get_podcast_or_404(podcast_id):
    return get_object_or_404(get_podcasts(), pk=podcast_id)


def get_podcast_detail_context(request, podcast, extra_context=None):

    return {
        "podcast": podcast,
        "has_similar": Recommendation.objects.filter(podcast=podcast).exists(),
        "num_episodes": Episode.objects.filter(podcast=podcast).count(),
    } | (extra_context or {})


def subscribe_action_response(request, podcast, is_subscribed):
    return TemplateResponse(
        request,
        "podcasts/actions/subscribe.html",
        {
            "podcast": podcast,
            "is_subscribed": is_subscribed,
        },
    )
