from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_safe

from simplecasts.http.request import AuthenticatedHttpRequest, HttpRequest
from simplecasts.http.response import RenderOrRedirectResponse
from simplecasts.models import Episode, Podcast
from simplecasts.services.search import search_queryset
from simplecasts.views.paginator import render_paginated_response


@require_safe
@login_required
def discover(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """Shows all promoted podcasts."""
    podcasts = (
        Podcast.objects.published()
        .filter(
            promoted=True,
            language=settings.DISCOVER_FEED_LANGUAGE,
            private=False,
        )
        .order_by("-pub_date")[: settings.DEFAULT_PAGE_SIZE]
    )

    return TemplateResponse(request, "podcasts/discover.html", {"podcasts": podcasts})


@require_safe
@login_required
def podcast_detail(
    request: AuthenticatedHttpRequest,
    podcast_id: int,
    slug: str,
) -> RenderOrRedirectResponse:
    """Details for a single podcast."""

    podcast = get_object_or_404(
        Podcast.objects.published().select_related("canonical"),
        pk=podcast_id,
    )

    is_subscribed = request.user.subscriptions.filter(podcast=podcast).exists()

    return TemplateResponse(
        request,
        "podcasts/detail.html",
        {
            "podcast": podcast,
            "is_subscribed": is_subscribed,
        },
    )


@require_safe
@login_required
def latest_episode(_, podcast_id: int) -> HttpResponseRedirect:
    """Redirects to latest episode."""
    if (
        episode := Episode.objects.filter(podcast__pk=podcast_id)
        .order_by("-pub_date", "-id")
        .first()
    ):
        return redirect(episode)
    raise Http404


@require_safe
@login_required
def episodes(
    request: HttpRequest,
    podcast_id: int,
    slug: str | None = None,
) -> TemplateResponse:
    """Render episodes for a single podcast."""
    podcast = get_object_or_404(Podcast.objects.published(), pk=podcast_id)
    podcast_episodes = podcast.episodes.select_related("podcast")

    default_ordering = "asc" if podcast.is_serial() else "desc"
    ordering = request.GET.get("order", default_ordering)
    order_by = ("pub_date", "id") if ordering == "asc" else ("-pub_date", "-id")

    if request.search:
        podcast_episodes = search_queryset(
            podcast_episodes,
            request.search.value,
            "search_vector",
        ).order_by("-rank", *order_by)
    else:
        podcast_episodes = podcast_episodes.order_by(*order_by)

    return render_paginated_response(
        request,
        "podcasts/episodes.html",
        podcast_episodes,
        {
            "podcast": podcast,
            "ordering": ordering,
        },
    )


@require_safe
@login_required
def season(
    request: HttpRequest,
    podcast_id: int,
    season: int,
    slug: str | None = None,
) -> TemplateResponse:
    """Render episodes for a podcast season."""
    podcast = get_object_or_404(Podcast.objects.published(), pk=podcast_id)

    podcast_episodes = podcast.episodes.filter(season=season).select_related("podcast")

    order_by = ("pub_date", "id") if podcast.is_serial() else ("-pub_date", "-id")
    podcast_episodes = podcast_episodes.order_by(*order_by)

    return render_paginated_response(
        request,
        "podcasts/season.html",
        podcast_episodes,
        {
            "podcast": podcast,
            "season": podcast.get_season(season),
        },
    )


@require_safe
@login_required
def similar(
    request: HttpRequest,
    podcast_id: int,
    slug: str | None = None,
) -> TemplateResponse:
    """List similar podcasts based on recommendations."""

    podcast = get_object_or_404(Podcast.objects.published(), pk=podcast_id)

    recommendations = podcast.recommendations.select_related("recommended").order_by(
        "-score"
    )[: settings.DEFAULT_PAGE_SIZE]

    return TemplateResponse(
        request,
        "podcasts/similar.html",
        {
            "podcast": podcast,
            "recommendations": recommendations,
        },
    )
