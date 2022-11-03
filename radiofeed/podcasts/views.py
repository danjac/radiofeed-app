from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Exists, OuterRef, QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST, require_safe
from django_htmx.http import HttpResponseClientRedirect
from ratelimit.decorators import ratelimit

from radiofeed.common.decorators import require_auth
from radiofeed.common.http import HttpResponseConflict
from radiofeed.common.pagination import render_pagination_response
from radiofeed.episodes.models import Episode
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Category, Podcast, Subscription


@require_safe
def intro(request: HttpRequest, limit: int = 30) -> HttpResponse:
    """Render default site home page for anonymous users."""
    if request.user.is_authenticated:
        url = reverse("podcasts:index")
        return HttpResponseClientRedirect(url) if request.htmx else redirect(url)

    podcasts = _get_podcasts().filter(promoted=True).order_by("-pub_date")[:limit]

    return render(request, "podcasts/intro.html", {"podcasts": podcasts})


@require_safe
@require_auth
def index(request: HttpRequest) -> HttpResponse:
    """Render default podcast home page for authenticated users."""
    podcasts = _get_podcasts().order_by("-pub_date")
    subscribed = set(request.user.subscriptions.values_list("podcast", flat=True))
    promoted = "promoted" in request.GET or not subscribed

    if promoted:
        podcasts = podcasts.filter(promoted=True)
    else:
        podcasts = podcasts.filter(pk__in=subscribed)

    return render_pagination_response(
        request,
        podcasts,
        "podcasts/index.html",
        {
            "promoted": promoted,
            "has_subscriptions": bool(subscribed),
        },
    )


@require_safe
@require_auth
def search_podcasts(request: HttpRequest) -> HttpResponse:
    """Render search page. Redirects to index page if search is empty."""
    if request.search:

        return render_pagination_response(
            request,
            (
                _get_podcasts()
                .search(request.search)
                .order_by(
                    "-rank",
                    "-pub_date",
                )
            ),
            "podcasts/search.html",
        )

    return redirect(settings.HOME_URL)


@ratelimit(key="ip", rate="20/m")
@require_auth
@require_safe
def search_itunes(request: HttpRequest) -> HttpResponse:
    """Render iTunes search page. Redirects to index page if search is empty."""
    if request.search:

        feeds: list[itunes.Feed] = []

        try:
            feeds = itunes.search_cached(request.search.value)
        except itunes.ItunesException:
            messages.error(
                request, _("Sorry, an error occurred trying to access iTunes.")
            )

        return render(
            request,
            "podcasts/itunes_search.html",
            {
                "feeds": feeds,
                "clear_search_url": reverse("podcasts:index"),
            },
        )

    return redirect(settings.HOME_URL)


@require_safe
@require_auth
def latest_episode(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:
    """Redirects to the latest episode for a given podcast."""
    if (
        episode := Episode.objects.filter(podcast=podcast_id)
        .order_by("-pub_date")
        .first()
    ) is None:
        raise Http404()

    return redirect(episode)


@require_safe
@require_auth
def podcast_detail(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:
    """Render details for a single podcast."""
    podcast = _get_podcast_or_404(podcast_id)

    return render(
        request,
        "podcasts/detail.html",
        {
            "podcast": podcast,
            "is_subscribed": podcast.is_subscribed(request.user),
        },
    )


@require_safe
@require_auth
def episodes(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:
    """Render episodes for a single podcast."""
    podcast = _get_podcast_or_404(podcast_id)
    episodes = podcast.episodes.select_related("podcast")

    if request.search:
        episodes = episodes.search(request.search).order_by("-rank", "-pub_date")
    else:
        episodes = episodes.order_by(
            "-pub_date" if request.sorter.is_desc else "pub_date"
        )

    return render_pagination_response(
        request,
        episodes,
        "podcasts/episodes.html",
        extra_context={
            "podcast": podcast,
            "is_podcast_detail": True,
        },
    )


@require_safe
@require_auth
def similar(
    request: HttpRequest, podcast_id: int, slug: str | None = None, limit: int = 12
) -> HttpResponse:
    """List similar podcasts based on recommendations."""
    podcast = _get_podcast_or_404(podcast_id)

    recommendations = podcast.recommendations.select_related("recommended").order_by(
        "-similarity",
        "-frequency",
    )[:limit]

    return render(
        request,
        "podcasts/similar.html",
        {
            "podcast": podcast,
            "recommendations": recommendations,
        },
    )


@require_safe
@require_auth
def category_list(request: HttpRequest) -> HttpResponse:
    """List all categories containing podcasts."""
    categories = (
        Category.objects.annotate(
            has_podcasts=Exists(_get_podcasts().filter(categories=OuterRef("pk")))
        )
        .filter(has_podcasts=True)
        .order_by("name")
    )

    if request.search:
        categories = categories.search(request.search)

    return render(request, "podcasts/categories.html", {"categories": categories})


@require_safe
@require_auth
def category_detail(
    request: HttpRequest, category_id: int, slug: str | None = None
) -> HttpResponse:
    """Render individual podcast category along with its podcasts.

    Podcasts can also be searched.
    """
    category = get_object_or_404(Category, pk=category_id)
    podcasts = _get_podcasts().filter(categories=category).distinct()

    if request.search:
        podcasts = podcasts.search(request.search).order_by(
            "-rank",
            "-pub_date",
        )
    else:
        podcasts = podcasts.order_by("-pub_date")

    return render_pagination_response(
        request,
        podcasts,
        "podcasts/category_detail.html",
        {"category": category},
    )


@require_POST
@require_auth
def subscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Subscribe a user to a podcast.

    Returns:
        returns HTTP CONFLICT if user is already subscribed to this podcast, otherwise returns the subscribe action as HTMX snippet.
    """
    podcast = _get_podcast_or_404(podcast_id)

    try:
        Subscription.objects.create(subscriber=request.user, podcast=podcast)
    except IntegrityError:
        return HttpResponseConflict()

    messages.success(request, _("You are now subscribed to this podcast"))
    return _render_subscribe_action(request, podcast, True)


@require_POST
@require_auth
def unsubscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Unsubscribe user from a podcast."""
    podcast = _get_podcast_or_404(podcast_id)

    Subscription.objects.filter(subscriber=request.user, podcast=podcast).delete()

    messages.info(request, _("You are no longer subscribed to this podcast"))
    return _render_subscribe_action(request, podcast, False)


def _get_podcasts() -> QuerySet[Podcast]:
    return Podcast.objects.filter(pub_date__isnull=False)


def _get_podcast_or_404(podcast_id: int) -> Podcast:
    return get_object_or_404(_get_podcasts(), pk=podcast_id)


def _render_subscribe_action(
    request: HttpRequest, podcast: Podcast, is_subscribed: bool
) -> HttpResponse:
    return render(
        request,
        "podcasts/includes/subscribe.html",
        {
            "podcast": podcast,
            "is_subscribed": is_subscribed,
        },
    )
