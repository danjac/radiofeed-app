from typing import List, Optional

from django.conf import settings
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from radiofeed.pagination import render_paginated_response

from .. import itunes
from ..models import Category, Podcast
from ..tasks import sync_podcast_feed


def index(request: HttpRequest) -> HttpResponse:
    categories = Category.objects.all()

    if request.search:
        categories = categories.search(request.search).order_by("-similarity", "name")
    else:
        categories = (
            categories.filter(parent__isnull=True)
            .prefetch_related(
                Prefetch(
                    "children",
                    queryset=Category.objects.order_by("name"),
                )
            )
            .order_by("name")
        )
    return TemplateResponse(
        request,
        "podcasts/categories.html",
        {"categories": categories},
    )


def category_detail(request: HttpRequest, category_id: int, slug: Optional[str] = None):
    category: Category = get_object_or_404(
        Category.objects.select_related("parent"), pk=category_id
    )

    if request.turbo.frame:

        podcasts = category.podcast_set.filter(pub_date__isnull=False)

        if request.search:
            podcasts = podcasts.search(request.search).order_by("-rank", "-pub_date")
        else:
            podcasts = podcasts.order_by("-pub_date")

        return render_paginated_response(
            request,
            podcasts,
            "podcasts/_podcast_list_cached.html",
            {"cache_timeout": settings.DEFAULT_CACHE_TIMEOUT},
        )

    return TemplateResponse(
        request,
        "podcasts/category.html",
        {"category": category, "children": category.children.order_by("name")},
    )


def itunes_category(request: HttpRequest, category_id: int) -> HttpResponse:
    error: bool = False
    results: itunes.SearchResultList = []
    new_podcasts: List[Podcast] = []

    category = get_object_or_404(
        Category.objects.select_related("parent").filter(itunes_genre_id__isnull=False),
        pk=category_id,
    )
    try:
        results, new_podcasts = itunes.fetch_itunes_genre(category.itunes_genre_id)
        error = False
    except (itunes.Timeout, itunes.Invalid):
        error = True

    for podcast in new_podcasts:
        sync_podcast_feed.delay(rss=podcast.rss)

    return TemplateResponse(
        request,
        "podcasts/itunes/category.html",
        {
            "category": category,
            "results": results,
            "error": error,
        },
    )
