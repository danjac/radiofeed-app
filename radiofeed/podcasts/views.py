from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Exists, OuterRef, QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST, require_safe

from radiofeed.decorators import (
    htmx_login_required,
    require_DELETE,
    require_form_methods,
)
from radiofeed.episodes.models import Episode
from radiofeed.http import HttpResponseConflict
from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes
from radiofeed.podcasts.forms import PrivateFeedForm
from radiofeed.podcasts.models import Category, Podcast

_discover_url = reverse_lazy("podcasts:discover")
_private_feeds_url = reverse_lazy("podcasts:private_feeds")


@require_safe
def index(request: HttpRequest) -> HttpResponse:
    """Returns landing page."""
    if request.user.is_authenticated:
        return redirect("podcasts:subscriptions")

    podcasts = _get_podcasts().filter(promoted=True).order_by("-pub_date")

    return render(request, "podcasts/landing_page.html", {"podcasts": podcasts})


@require_safe
@login_required
def subscriptions(request: HttpRequest) -> HttpResponse:
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

    if not podcasts.exists():
        return redirect("podcasts:discover")

    podcasts = (
        podcasts.search(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )
        if request.search
        else podcasts.order_by("-pub_date")
    )

    return render(request, "podcasts/subscriptions.html", {"podcasts": podcasts})


@require_safe
@login_required
def discover(request: HttpRequest) -> HttpResponse:
    """Shows all promoted podcasts. If search, will search all
    public podcasts in database."""

    podcasts = (
        (
            _get_podcasts()
            .filter(private=False)
            .search(request.search.value)
            .order_by(
                "-exact_match",
                "-rank",
                "-pub_date",
            )
        )
        if request.search
        else _get_podcasts().filter(promoted=True).order_by("-pub_date")
    )

    return render(request, "podcasts/discover.html", {"podcasts": podcasts})


@require_safe
@login_required
def search_itunes(request: HttpRequest) -> HttpResponse:
    """Render iTunes search page. Redirects to index page if search is empty."""
    if request.search:
        try:
            feeds = itunes.search(get_client(), request.search.value)
            return render(
                request,
                "podcasts/search_itunes.html",
                {
                    "feeds": feeds,
                    "clear_search_url": _discover_url,
                },
            )

        except itunes.ItunesError:
            messages.error(request, "Error: iTunes unavailable")

    return redirect(_discover_url)


@require_safe
@login_required
def latest_episode(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:
    """Redirects to the latest episode for a given podcast."""
    if (
        episode := Episode.objects.filter(podcast=podcast_id)
        .order_by("-pub_date")
        .first()
    ) is None:
        raise Http404

    return redirect(episode)


@require_safe
@login_required
def podcast_detail(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:
    """Details for a single podcast."""

    podcast = _get_podcast_or_404(podcast_id)

    is_subscribed = request.user.subscriptions.filter(podcast=podcast).exists()

    return render(
        request,
        "podcasts/detail.html",
        {
            "podcast": podcast,
            "is_subscribed": is_subscribed,
        },
    )


@require_safe
@login_required
def episodes(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:
    """Render episodes for a single podcast."""
    podcast = _get_podcast_or_404(podcast_id)

    episodes = podcast.episodes.select_related("podcast")
    ordering_asc = request.GET.get("order", "desc") == "asc"

    if request.search:
        episodes = episodes.search(request.search.value).order_by("-rank", "-pub_date")
    else:
        episodes = episodes.order_by("pub_date" if ordering_asc else "-pub_date")

    return render(
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
    limit: int = 12,
) -> HttpResponse:
    """List similar podcasts based on recommendations."""

    podcast = _get_podcast_or_404(podcast_id)

    recommendations = (
        podcast.recommendations.with_relevance()
        .select_related("recommended")
        .order_by("-relevance")[:limit]
    )

    return render(
        request,
        "podcasts/similar.html",
        {
            "podcast": podcast,
            "recommendations": recommendations,
        },
    )


@require_safe
@login_required
def category_list(request: HttpRequest) -> HttpResponse:
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

    return render(
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
) -> HttpResponse:
    """Render individual podcast category along with its podcasts.

    Podcasts can also be searched.
    """
    category = get_object_or_404(Category, pk=category_id)
    podcasts = category.podcasts.filter(private=False, pub_date__isnull=False)

    if request.search:
        podcasts = podcasts.search(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )
    else:
        podcasts = podcasts.order_by("-pub_date")

    return render(
        request,
        "podcasts/category_detail.html",
        {
            "category": category,
            "podcasts": podcasts,
            "search_podcasts_url": _discover_url,
        },
    )


@require_POST
@htmx_login_required
def subscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:
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
def unsubscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Unsubscribe user from a podcast."""
    podcast = _get_podcast_or_404(podcast_id, private=False)
    request.user.subscriptions.filter(podcast=podcast).delete()
    messages.info(request, "Unsubscribed from Podcast")
    return _render_subscribe_action(request, podcast, is_subscribed=False)


@require_safe
@login_required
def private_feeds(request: HttpRequest) -> HttpResponse:
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

    if request.search:
        podcasts = podcasts.search(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )
    else:
        podcasts = podcasts.order_by("-pub_date")

    return render(
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
) -> HttpResponse:
    """Add new private feed to collection."""
    if request.method == "POST":
        form = PrivateFeedForm(request.user, request.POST)
        if form.is_valid():
            podcast, is_new = form.save()

            if is_new:
                messages.success(
                    request,
                    "Podcast added to your Private Feeds and will appear here soon",
                )
                return redirect(_private_feeds_url)

            messages.success(request, "Podcast added to your Private Feeds")
            return redirect(podcast)
    else:
        form = PrivateFeedForm(request.user)

    return render(request, "podcasts/private_feed_form.html", {"form": form})


@require_DELETE
@htmx_login_required
def remove_private_feed(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Removes subscription to private feed."""
    podcast = _get_podcast_or_404(podcast_id, private=True)
    request.user.subscriptions.filter(podcast=podcast).delete()
    messages.info(request, "Removed from Private Feeds")
    return redirect(_private_feeds_url)


def _get_podcast_or_404(podcast_id: int, **kwargs) -> Podcast:
    return get_object_or_404(_get_podcasts(), pk=podcast_id, **kwargs)


def _get_podcasts() -> QuerySet[Podcast]:
    return Podcast.objects.filter(pub_date__isnull=False)


def _render_subscribe_action(
    request: HttpRequest, podcast: Podcast, *, is_subscribed: bool
) -> HttpResponse:
    return render(
        request,
        "podcasts/detail.html#subscribe_button",
        {
            "podcast": podcast,
            "is_subscribed": is_subscribed,
        },
    )
