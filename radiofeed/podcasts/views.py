import contextlib
from typing import TYPE_CHECKING, cast

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Exists, OuterRef, QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_safe

from radiofeed.http import HttpResponseConflict, require_DELETE, require_form_methods
from radiofeed.http_client import get_client
from radiofeed.paginator import render_pagination
from radiofeed.partials import render_partial_for_target
from radiofeed.podcasts import itunes
from radiofeed.podcasts.forms import PrivateFeedForm
from radiofeed.podcasts.models import Category, Podcast

if TYPE_CHECKING:
    from radiofeed.users.models import User  # pragma: no cover


@require_safe
@login_required
def subscriptions(request: HttpRequest) -> HttpResponse:
    """Render podcast index page."""
    podcasts = _get_podcasts().subscribed(request.user).distinct()

    if request.search:
        podcasts = podcasts.search(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )
    else:
        podcasts = podcasts.order_by("-pub_date")

    return render_pagination(request, "podcasts/subscriptions.html", podcasts)


@require_safe
@login_required
def discover(request: HttpRequest) -> HttpResponse:
    """Shows all promoted podcasts."""
    podcasts = (
        _get_podcasts()
        .filter(promoted=True)
        .order_by("-pub_date")[: settings.DEFAULT_PAGE_SIZE]
    )

    return render(
        request,
        "podcasts/discover.html",
        {
            "podcasts": podcasts,
        },
    )


@require_safe
@login_required
def search_podcasts(
    request: HttpRequest,
) -> HttpResponse:
    """Search all public podcasts in database."""

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

        return render_pagination(request, "podcasts/search_podcasts.html", podcasts)

    return redirect("podcasts:discover")


@require_safe
@login_required
def search_itunes(request: HttpRequest) -> HttpResponse:
    """Render iTunes search page. Redirects to discover page if search is empty."""

    if request.search:
        try:
            feeds = itunes.search_from_cache(get_client(), request.search.value)
            return render(
                request,
                "podcasts/search_itunes.html",
                {
                    "feeds": feeds,
                },
            )
        except itunes.ItunesError as e:
            messages.error(request, f"Failed to search iTunes: {e}")

    return redirect("podcasts:discover")


@require_safe
@login_required
def podcast_detail(request: HttpRequest, podcast_id: int, slug: str) -> HttpResponse:
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
def latest_episode(_, podcast_id: int) -> HttpResponse:
    """Redirects to latest episode."""
    podcast = _get_podcast_or_404(podcast_id)
    if episode := podcast.episodes.order_by("-pub_date").first():
        return redirect(episode)
    raise Http404


@require_safe
@login_required
def episodes(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:
    """Render episodes for a single podcast."""
    podcast = _get_podcast_or_404(podcast_id)

    episodes = podcast.episodes.select_related("podcast")

    ordering: str = "desc"
    season: int | None = None

    if request.search:
        episodes = episodes.search(request.search.value).order_by(
            "-rank",
            "-pub_date",
        )
    else:
        default_ordering = "asc" if podcast.is_serial() else "desc"
        ordering = request.GET.get("order", default_ordering)

        with contextlib.suppress(ValueError):
            if season := int(request.GET.get("season", "")):
                episodes = episodes.filter(season=season)

        episodes = episodes.order_by("pub_date" if ordering == "asc" else "-pub_date")

    return render_pagination(
        request,
        "podcasts/episodes.html",
        episodes,
        {
            "podcast": podcast,
            "ordering": ordering,
            "season": season,
        },
    )


@require_safe
@login_required
def similar(
    request: HttpRequest,
    podcast_id: int,
    slug: str | None = None,
) -> HttpResponse:
    """List similar podcasts based on recommendations."""

    podcast = _get_podcast_or_404(podcast_id)

    recommendations = podcast.recommendations.select_related("recommended").order_by(
        "-score"
    )[: settings.DEFAULT_PAGE_SIZE]

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
        Category.objects.alias(
            has_podcasts=Exists(
                _get_podcasts().filter(
                    categories=OuterRef("pk"),
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

    podcasts = category.podcasts.published().filter(private=False).distinct()

    if request.search:
        podcasts = podcasts.search(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )
    else:
        podcasts = podcasts.order_by("-pub_date")

    return render_pagination(
        request,
        "podcasts/category_detail.html",
        podcasts,
        {
            "category": category,
        },
    )


@require_POST
@login_required
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
@login_required
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
    podcasts = _get_podcasts().subscribed(request.user).filter(private=True).distinct()

    if request.search:
        podcasts = podcasts.search(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )
    else:
        podcasts = podcasts.order_by("-pub_date")

    return render_pagination(request, "podcasts/private_feeds.html", podcasts)


@require_form_methods
@login_required
def add_private_feed(
    request: HttpRequest,
) -> HttpResponse:
    """Add new private feed to collection."""

    user = cast("User", request.user)

    if request.method == "POST":
        form = PrivateFeedForm(request.POST, user=user)

        if form.is_valid():
            podcast, is_new = form.save()
            if is_new:
                messages.success(
                    request,
                    "Podcast added to your Private Feeds and will appear here soon",
                )
                return redirect("podcasts:private_feeds")

            messages.success(request, "Podcast added to your Private Feeds")
            return redirect(podcast)
    else:
        form = PrivateFeedForm(user=user)

    return render_partial_for_target(
        request,
        "podcasts/private_feed_form.html",
        {
            "form": form,
        },
        target="private-feed-form",
        partial="form",
    )


@require_DELETE
@login_required
def remove_private_feed(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Delete private feed."""

    _get_podcast_or_404(
        podcast_id,
        private=True,
        subscriptions__subscriber=request.user,
    ).delete()

    messages.info(request, "Removed from Private Feeds")
    return redirect("podcasts:private_feeds")


def _get_podcasts() -> QuerySet[Podcast]:
    return Podcast.objects.published()


def _get_podcast_or_404(podcast_id: int, **kwargs) -> Podcast:
    return get_object_or_404(_get_podcasts(), pk=podcast_id, **kwargs)


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
