from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Exists, OuterRef
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_POST, require_safe

from listenwave.decorators import require_DELETE, require_form_methods
from listenwave.http_client import get_client
from listenwave.paginator import render_paginated_response
from listenwave.partials import render_partial_response
from listenwave.podcasts import itunes
from listenwave.podcasts.forms import PodcastForm
from listenwave.podcasts.models import Category, Podcast, PodcastQuerySet
from listenwave.request import AuthenticatedHttpRequest, HttpRequest
from listenwave.response import HttpResponseConflict, RenderOrRedirectResponse
from listenwave.search import search_queryset


@require_safe
@login_required
def subscriptions(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """Render podcast index page."""
    podcasts = _get_podcasts().subscribed(request.user).distinct()

    if request.search:
        podcasts = search_queryset(
            podcasts,
            request.search.value,
            "search_vector",
        ).order_by("-rank", "-pub_date")
    else:
        podcasts = podcasts.order_by("-pub_date")

    return render_paginated_response(request, "podcasts/subscriptions.html", podcasts)


@require_safe
@login_required
def discover(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """Shows all promoted podcasts."""
    podcasts = (
        _get_podcasts()
        .filter(
            promoted__isnull=False,
            language=settings.DISCOVER_FEED_LANGUAGE,
        )
        .order_by("-promoted", "-pub_date")[: settings.DEFAULT_PAGE_SIZE]
    )

    return TemplateResponse(request, "podcasts/discover.html", {"podcasts": podcasts})


@require_safe
@login_required
def search_podcasts(request: HttpRequest) -> RenderOrRedirectResponse:
    """Search all public podcasts in database. Redirects to discover page if search is empty."""

    if request.search:
        podcasts = search_queryset(
            _get_podcasts().filter(private=False),
            request.search.value,
            "search_vector",
        ).order_by("-rank", "-pub_date")

        return render_paginated_response(
            request, "podcasts/search_podcasts.html", podcasts
        )

    return _redirect_to_discover_page()


@require_safe
@login_required
def search_itunes(request: HttpRequest) -> RenderOrRedirectResponse:
    """Render iTunes search page. Redirects to discover page if search is empty."""

    if request.search:
        try:
            with get_client() as client:
                feeds = itunes.search_cached(client, request.search.value)
            return TemplateResponse(
                request,
                "podcasts/search_itunes.html",
                {
                    "feeds": feeds,
                },
            )
        except itunes.ItunesError as exc:
            messages.error(request, f"Failed to search iTunes: {exc}")

    return _redirect_to_discover_page()


@require_safe
@login_required
def search_people(request: HttpRequest) -> RenderOrRedirectResponse:
    """Search all podcasts by owner(s). Redirects to discover page if no owner is given."""

    if request.search:
        podcasts = search_queryset(
            _get_podcasts().filter(private=False),
            request.search.value,
            "owner_search_vector",
        ).order_by("-rank", "-pub_date")
        return render_paginated_response(
            request,
            "podcasts/search_people.html",
            podcasts,
        )

    return _redirect_to_discover_page()


@require_safe
@login_required
def podcast_detail(
    request: AuthenticatedHttpRequest,
    podcast_id: int,
    slug: str,
) -> TemplateResponse:
    """Details for a single podcast."""

    podcast = _get_podcast_or_404(podcast_id)

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
    podcast = _get_podcast_or_404(podcast_id)
    if episode := podcast.episodes.order_by("-pub_date", "-id").first():
        return HttpResponseRedirect(episode.get_absolute_url())
    raise Http404


@require_safe
@login_required
def episodes(
    request: HttpRequest,
    podcast_id: int,
    slug: str | None = None,
) -> TemplateResponse:
    """Render episodes for a single podcast."""
    podcast = _get_podcast_or_404(podcast_id)
    episodes = podcast.episodes.select_related("podcast")

    default_ordering = "asc" if podcast.is_serial() else "desc"
    ordering = request.GET.get("order", default_ordering)
    order_by = ("pub_date", "id") if ordering == "asc" else ("-pub_date", "-id")

    if request.search:
        episodes = search_queryset(
            episodes,
            request.search.value,
            "search_vector",
        ).order_by("-rank", *order_by)
    else:
        episodes = episodes.order_by(*order_by)

    return render_paginated_response(
        request,
        "podcasts/episodes.html",
        episodes,
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
    podcast = _get_podcast_or_404(podcast_id)

    episodes = podcast.episodes.filter(season=season).select_related("podcast")

    order_by = ("pub_date", "id") if podcast.is_serial() else ("-pub_date", "-id")
    episodes = episodes.order_by(*order_by)

    return render_paginated_response(
        request,
        "podcasts/season.html",
        episodes,
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

    podcast = _get_podcast_or_404(podcast_id)

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


@require_safe
@login_required
def category_list(request: HttpRequest) -> TemplateResponse:
    """List all categories containing podcasts."""
    categories = Category.objects.alias(
        has_podcasts=Exists(
            _get_podcasts().filter(
                categories=OuterRef("pk"),
                private=False,
            )
        )
    ).filter(has_podcasts=True)

    if request.search:
        categories = search_queryset(
            categories,
            request.search.value,
            "search_vector",
        ).order_by("-rank", "name")
    else:
        categories = categories.order_by("name")

    return TemplateResponse(
        request,
        "podcasts/categories.html",
        {
            "categories": categories,
        },
    )


@require_safe
@login_required
def category_detail(request: HttpRequest, slug: str) -> TemplateResponse:
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
        "podcasts/category_detail.html",
        podcasts,
        {
            "category": category,
        },
    )


@require_POST
@login_required
def subscribe(
    request: AuthenticatedHttpRequest, podcast_id: int
) -> TemplateResponse | HttpResponseConflict:
    """Subscribe a user to a podcast. Podcast must be active and public."""
    podcast = _get_podcast_or_404(podcast_id, private=False)

    try:
        request.user.subscriptions.create(podcast=podcast)
    except IntegrityError:
        return HttpResponseConflict()

    messages.success(request, "Subscribed to Podcast")

    return _render_subscribe_action(request, podcast, is_subscribed=True)


@require_DELETE
@login_required
def unsubscribe(request: AuthenticatedHttpRequest, podcast_id: int) -> TemplateResponse:
    """Unsubscribe user from a podcast."""
    podcast = _get_podcast_or_404(podcast_id, private=False)
    request.user.subscriptions.filter(podcast=podcast).delete()
    messages.info(request, "Unsubscribed from Podcast")
    return _render_subscribe_action(request, podcast, is_subscribed=False)


@require_safe
@login_required
def private_feeds(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """Lists user's private feeds."""
    podcasts = _get_podcasts().subscribed(request.user).filter(private=True)

    if request.search:
        podcasts = search_queryset(
            podcasts,
            request.search.value,
            "search_vector",
        ).order_by("-rank", "-pub_date")
    else:
        podcasts = podcasts.order_by("-pub_date")

    return render_paginated_response(request, "podcasts/private_feeds.html", podcasts)


@require_form_methods
@login_required
def add_private_feed(
    request: AuthenticatedHttpRequest,
) -> RenderOrRedirectResponse:
    """Add new private feed to collection."""
    if request.method == "POST":
        form = PodcastForm(request.POST)
        if form.is_valid():
            podcast = form.save(commit=False)
            podcast.private = True
            podcast.save()

            request.user.subscriptions.create(podcast=podcast)

            messages.success(
                request,
                "Podcast added to your Private Feeds and will appear here soon",
            )
            return HttpResponseRedirect(reverse("podcasts:private_feeds"))
    else:
        form = PodcastForm()

    return render_partial_response(
        request,
        "podcasts/private_feed_form.html",
        {"form": form},
        target="private-feed-form",
        partial="form",
    )


@require_DELETE
@login_required
def remove_private_feed(
    request: AuthenticatedHttpRequest,
    podcast_id: int,
) -> HttpResponseRedirect:
    """Delete private feed."""

    _get_podcast_or_404(
        podcast_id,
        private=True,
        subscriptions__subscriber=request.user,
    ).delete()

    messages.info(request, "Removed from Private Feeds")
    return HttpResponseRedirect(reverse("podcasts:private_feeds"))


def _get_podcasts() -> PodcastQuerySet:
    return Podcast.objects.published()


def _get_podcast_or_404(podcast_id: int, **kwargs) -> Podcast:
    return get_object_or_404(_get_podcasts(), pk=podcast_id, **kwargs)


def _redirect_to_discover_page() -> HttpResponseRedirect:
    return HttpResponseRedirect(reverse("podcasts:discover"))


def _render_subscribe_action(
    request: HttpRequest,
    podcast: Podcast,
    *,
    is_subscribed: bool,
) -> TemplateResponse:
    return TemplateResponse(
        request,
        "podcasts/detail.html#subscribe_button",
        {
            "podcast": podcast,
            "is_subscribed": is_subscribed,
        },
    )
