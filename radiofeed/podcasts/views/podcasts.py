from typing import Dict, List, Optional

from django.conf import settings
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from radiofeed.pagination import render_paginated_response

from .. import itunes
from ..models import Podcast
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
