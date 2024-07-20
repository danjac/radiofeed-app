from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Exists, OuterRef, Q, QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_POST, require_safe

from radiofeed.decorators import (
    htmx_login_required,
    require_DELETE,
    require_form_methods,
)
from radiofeed.episodes.models import Episode
from radiofeed.http import HttpResponseConflict
from radiofeed.http_client import get_client
from radiofeed.pagination import PAGE_SIZE
from radiofeed.podcasts import itunes
from radiofeed.podcasts.forms import PrivateFeedForm
from radiofeed.podcasts.models import Category, Podcast


@require_safe
def index(request: HttpRequest) -> HttpResponse:
    """Returns landing page."""
    if request.user.is_anonymous:
        podcasts = _get_promoted_podcasts().order_by("-pub_date")

        return TemplateResponse(
            request,
            "podcasts/landing_page.html",
            {
                "podcasts": podcasts,
            },
        )

    return HttpResponseRedirect(reverse("podcasts:subscriptions"))


@require_safe
@login_required
def subscriptions(request: HttpRequest) -> TemplateResponse:
    """Render podcast index page.
    If user does not have any subscribed podcasts, redirects to Discover page.
    """
    podcasts = (
        _get_podcasts()
        .annotate(
            is_subscribed=Exists(
                request.user.subscriptions.filter(
                    podcast=OuterRef("pk"),
                )
            )
        )
        .filter(is_subscribed=True)
    )

    podcasts = (
        podcasts.search(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )
        if request.search
        else podcasts.order_by("-pub_date")
    )

    return TemplateResponse(
        request,
        "podcasts/subscriptions.html",
        {
            "podcasts": podcasts,
        },
    )


@require_safe
@login_required
def discover(request: HttpRequest) -> TemplateResponse:
    """Shows all promoted podcasts."""

    podcasts = (
        Podcast.objects.annotate(
            is_recommended=Exists(
                request.user.recommended_podcasts.filter(pk=OuterRef("pk"))
            )
            & ~Exists(
                request.user.subscriptions.filter(
                    podcast=OuterRef("pk"),
                )
            ),
        )
        .filter(Q(promoted=True) | Q(is_recommended=True))
        .order_by("-pub_date")
    )

    return TemplateResponse(
        request,
        "podcasts/discover.html",
        {
            "podcasts": podcasts,
            "search_url": reverse("podcasts:search_podcasts"),
        },
    )


@require_safe
@login_required
def search_podcasts(request: HttpRequest) -> HttpResponseRedirect | TemplateResponse:
    """Search all public podcasts in database."""

    discover_url = reverse("podcasts:discover")

    if request.search:
        podcasts = (
            _get_podcasts()
            .filter(private=False)
            .search(request.search.value)
            .order_by(
                "-exact_match",
                "-rank",
                "-pub_date",
            )
        )

        return TemplateResponse(
            request,
            "podcasts/search.html",
            {
                "podcasts": podcasts,
                "clear_search_url": discover_url,
            },
        )

    return HttpResponseRedirect(discover_url)


@require_safe
@login_required
def search_itunes(request: HttpRequest) -> HttpResponseRedirect | TemplateResponse:
    """Render iTunes search page. Redirects to discover page if search is empty."""
    discover_url = reverse("podcasts:discover")

    if request.search:
        feeds = itunes.search(get_client(), request.search.value)

        return TemplateResponse(
            request,
            "podcasts/search_itunes.html",
            {
                "feeds": feeds,
                "clear_search_url": reverse("podcasts:discover"),
            },
        )

    return HttpResponseRedirect(discover_url)


@require_safe
@login_required
def podcast_detail(
    request: HttpRequest, podcast_id: int, slug: str
) -> TemplateResponse:
    """Details for a single podcast."""

    podcast = _get_podcast_or_404(podcast_id)

    is_subscribed = request.user.subscriptions.filter(podcast=podcast).exists()

    latest_episode = (
        Episode.objects.filter(podcast=podcast_id).order_by("-pub_date").first()
    )

    return TemplateResponse(
        request,
        "podcasts/detail.html",
        {
            "podcast": podcast,
            "is_subscribed": is_subscribed,
            "latest_episode": latest_episode,
        },
    )


@require_safe
@login_required
def episodes(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> TemplateResponse:
    """Render episodes for a single podcast."""
    podcast = _get_podcast_or_404(podcast_id)

    episodes = podcast.episodes.select_related("podcast")
    ordering_asc = request.GET.get("order", "desc") == "asc"

    episodes = (
        episodes.search(request.search.value).order_by("-rank", "-pub_date")
        if request.search
        else episodes.order_by("pub_date" if ordering_asc else "-pub_date")
    )

    return TemplateResponse(
        request,
        "podcasts/episodes.html",
        {
            "podcast": podcast,
            "episodes": episodes,
            "ordering_asc": ordering_asc,
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

    recommendations = (
        podcast.recommendations.with_relevance()
        .select_related("recommended")
        .order_by("-relevance")[:PAGE_SIZE]
    )

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
    categories = (
        Category.objects.annotate(
            has_podcasts=Exists(
                Podcast.objects.filter(
                    categories=OuterRef("pk"),
                    pub_date__isnull=False,
                    private=False,
                )
            )
        )
        .filter(has_podcasts=True)
        .order_by("name")
    )

    if request.search:
        categories = categories.search(request.search.value)

    return TemplateResponse(
        request,
        "podcasts/categories.html",
        {
            "categories": categories,
        },
    )


@require_safe
@login_required
def category_detail(
    request: HttpRequest, category_id: int, slug: str | None = None
) -> TemplateResponse:
    """Render individual podcast category along with its podcasts.

    Podcasts can also be searched.
    """
    category = get_object_or_404(Category, pk=category_id)
    podcasts = category.podcasts.filter(private=False, pub_date__isnull=False)

    podcasts = (
        podcasts.search(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )
        if request.search
        else podcasts.order_by("-pub_date")
    )

    return TemplateResponse(
        request,
        "podcasts/category_detail.html",
        {
            "category": category,
            "podcasts": podcasts,
        },
    )


@require_POST
@htmx_login_required
def subscribe(
    request: HttpRequest, podcast_id: int
) -> HttpResponseConflict | TemplateResponse:
    """Subscribe a user to a podcast. Podcast must be active and public."""
    podcast = _get_podcast_or_404(podcast_id, private=False)
    try:
        request.user.subscriptions.create(podcast=podcast)
    except IntegrityError:
        return HttpResponseConflict()

    messages.success(request, "Subscribed to Podcast")

    return _render_subscribe_action(request, podcast, is_subscribed=True)


@require_DELETE
@htmx_login_required
def unsubscribe(request: HttpRequest, podcast_id: int) -> TemplateResponse:
    """Unsubscribe user from a podcast."""
    podcast = _get_podcast_or_404(podcast_id, private=False)
    request.user.subscriptions.filter(podcast=podcast).delete()
    messages.info(request, "Unsubscribed from Podcast")
    return _render_subscribe_action(request, podcast, is_subscribed=False)


@require_safe
@login_required
def private_feeds(request: HttpRequest) -> TemplateResponse:
    """Lists user's private feeds."""
    podcasts = (
        _get_podcasts()
        .annotate(
            is_subscribed=Exists(
                request.user.subscriptions.filter(
                    podcast=OuterRef("pk"),
                )
            )
        )
        .filter(private=True, is_subscribed=True)
    )

    podcasts = (
        podcasts.search(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )
        if request.search
        else podcasts.order_by("-pub_date")
    )

    return TemplateResponse(
        request,
        "podcasts/private_feeds.html",
        {
            "podcasts": podcasts,
        },
    )


@require_form_methods
@login_required
def add_private_feed(
    request: HttpRequest,
) -> HttpResponseRedirect | TemplateResponse:
    """Add new private feed to collection."""
    if request.method == "POST":
        form = PrivateFeedForm(request.user, request.POST)
        if form.is_valid():
            podcast, is_new = form.save()
            if is_new:
                success_message = (
                    "Podcast added to your Private Feeds and will appear here soon"
                )
                redirect_url = reverse("podcasts:private_feeds")
            else:
                success_message = "Podcast added to your Private Feeds"
                redirect_url = podcast.get_absolute_url()

            messages.success(request, success_message)
            return HttpResponseRedirect(redirect_url)
    else:
        form = PrivateFeedForm(request.user)

    return TemplateResponse(
        request,
        "podcasts/private_feed_form.html",
        {
            "form": form,
        },
    )


@require_DELETE
@htmx_login_required
def remove_private_feed(request: HttpRequest, podcast_id: int) -> HttpResponseRedirect:
    """Removes subscription to private feed."""
    podcast = _get_podcast_or_404(podcast_id, private=True)
    request.user.subscriptions.filter(podcast=podcast).delete()
    messages.info(request, "Removed from Private Feeds")
    return HttpResponseRedirect(reverse("podcasts:private_feeds"))


def _get_podcast_or_404(podcast_id: int, **kwargs) -> Podcast:
    return get_object_or_404(_get_podcasts(), pk=podcast_id, **kwargs)


def _get_podcasts() -> QuerySet[Podcast]:
    return Podcast.objects.filter(pub_date__isnull=False)


def _get_promoted_podcasts() -> QuerySet[Podcast]:
    return _get_podcasts().filter(promoted=True)


def _render_subscribe_action(
    request: HttpRequest, podcast: Podcast, *, is_subscribed: bool
) -> TemplateResponse:
    return TemplateResponse(
        request,
        "podcasts/_subscribe_button.html",
        {
            "podcast": podcast,
            "is_subscribed": is_subscribed,
        },
    )
