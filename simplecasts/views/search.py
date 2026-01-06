from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_safe

from simplecasts.http.request import HttpRequest
from simplecasts.http.response import RenderOrRedirectResponse
from simplecasts.models import Episode, Podcast
from simplecasts.models.search import search_queryset
from simplecasts.services import itunes
from simplecasts.services.http_client import get_client
from simplecasts.views.paginator import render_paginated_response


@require_safe
@login_required
def search_episodes(request: HttpRequest) -> RenderOrRedirectResponse:
    """Search any episodes in the database."""

    if request.search:
        results = (
            search_queryset(
                Episode.objects.filter(podcast__private=False),
                request.search.value,
                "search_vector",
            )
            .select_related("podcast")
            .order_by("-rank", "-pub_date")
        )

        return render_paginated_response(
            request, "search/search_episodes.html", results
        )

    return redirect("episodes:index")


@require_safe
@login_required
def search_podcasts(request: HttpRequest) -> RenderOrRedirectResponse:
    """Search all public podcasts in database. Redirects to discover page if search is empty."""

    if request.search:
        results = search_queryset(
            Podcast.objects.published().filter(private=False),
            request.search.value,
            "search_vector",
        ).order_by("-rank", "-pub_date")

        return render_paginated_response(
            request, "search/search_podcasts.html", results
        )

    return redirect("podcasts:discover")


@require_safe
@login_required
def search_itunes(request: HttpRequest) -> RenderOrRedirectResponse:
    """Render iTunes search page. Redirects to discover page if search is empty."""

    if request.search:
        try:
            with get_client() as client:
                feeds, is_new = itunes.search_cached(
                    client,
                    request.search.value,
                    limit=settings.DEFAULT_PAGE_SIZE,
                )
                if is_new:
                    itunes.save_feeds_to_db(feeds)
            return TemplateResponse(
                request,
                "search/search_itunes.html",
                {
                    "feeds": feeds,
                },
            )
        except itunes.ItunesError as exc:
            messages.error(request, f"Failed to search iTunes: {exc}")

    return redirect("podcasts:discover")


@require_safe
@login_required
def search_people(request: HttpRequest) -> RenderOrRedirectResponse:
    """Search all podcasts by owner(s). Redirects to discover page if no owner is given."""

    if request.search:
        results = search_queryset(
            Podcast.objects.published().filter(private=False),
            request.search.value,
            "owner_search_vector",
        ).order_by("-rank", "-pub_date")
        return render_paginated_response(
            request,
            "search/search_people.html",
            results,
        )

    return redirect("podcasts:discover")
