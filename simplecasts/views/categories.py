from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_safe

from simplecasts.http.request import HttpRequest
from simplecasts.models import Category, Podcast
from simplecasts.services.search import search_queryset
from simplecasts.views.paginator import render_paginated_response


@require_safe
@login_required
def index(request: HttpRequest) -> TemplateResponse:
    """List all categories containing podcasts."""
    categories = (
        Category.objects.alias(
            has_podcasts=Exists(
                Podcast.objects.published()
                .filter(private=False)
                .filter(categories=OuterRef("pk"))
            )
        )
        .filter(has_podcasts=True)
        .order_by("name")
    )

    return TemplateResponse(
        request,
        "categories/index.html",
        {
            "categories": categories,
        },
    )


@require_safe
@login_required
def detail(request: HttpRequest, slug: str) -> TemplateResponse:
    """Render individual podcast category along with its podcasts.

    Podcasts can also be searched.
    """
    category = get_object_or_404(Category, slug=slug)

    podcasts = category.podcasts.published().filter(private=False).distinct()

    if request.search:
        podcasts = search_queryset(
            podcasts,
            request.search.value,
            "search_vector",
        ).order_by("-rank", "-pub_date")
    else:
        podcasts = podcasts.order_by("-pub_date")

    return render_paginated_response(
        request,
        "categories/category_detail.html",
        podcasts,
        {
            "category": category,
        },
    )
