from typing import cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Exists, OuterRef, QuerySet
from django.http import Http404, HttpRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_POST, require_safe

from radiofeed.http import HttpResponseConflict, require_DELETE, require_form_methods
from radiofeed.http_client import get_client
from radiofeed.paginator import DEFAULT_PAGE_SIZE, render_pagination_response
from radiofeed.partials import render_partial_for_target
from radiofeed.podcasts import itunes
from radiofeed.podcasts.forms import PrivateFeedForm
from radiofeed.podcasts.models import Category, Podcast
from radiofeed.users.models import User


@require_safe
@login_required
def subscriptions(request: HttpRequest) -> TemplateResponse:
    """Render podcast index page."""
    podcasts = _get_podcasts().subscribed(request.user).distinct()

    podcasts = (
        podcasts.search(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )
        if request.search
        else podcasts.order_by("-pub_date")
    )

    return render_pagination_response(request, "podcasts/subscriptions.html", podcasts)


@require_safe
@login_required
def discover(request: HttpRequest) -> TemplateResponse:
    """Shows all promoted podcasts."""
    podcasts = _get_podcasts().filter(promoted=True).order_by("-pub_date")
    return render_pagination_response(request, "podcasts/discover.html", podcasts)


@require_safe
@login_required
def search_podcasts(
    request: HttpRequest,
) -> HttpResponseRedirect | TemplateResponse:
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

        return render_pagination_response(
            request, "podcasts/search_podcasts.html", podcasts
        )

    return HttpResponseRedirect(reverse("podcasts:discover"))


@require_safe
@login_required
def search_itunes(request: HttpRequest) -> HttpResponseRedirect | TemplateResponse:
    """Render iTunes search page. Redirects to discover page if search is empty."""

    if request.search:
        feeds = itunes.search(
            get_client(),
            request.search.value,
            limit=DEFAULT_PAGE_SIZE,
        )

        return TemplateResponse(
            request,
            "podcasts/search_itunes.html",
            {
                "feeds": feeds,
            },
        )

    return HttpResponseRedirect(reverse("podcasts:discover"))


@require_safe
@login_required
def podcast_detail(
    request: HttpRequest, podcast_id: int, slug: str
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
    if episode := podcast.episodes.order_by("-pub_date").first():
        return HttpResponseRedirect(episode.get_absolute_url())
    raise Http404


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

    return render_pagination_response(
        request,
        "podcasts/episodes.html",
        episodes,
        {
            "podcast": podcast,
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
        .order_by("-relevance")[:DEFAULT_PAGE_SIZE]
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

    podcasts = category.podcasts.published().filter(private=False).distinct()

    podcasts = (
        podcasts.search(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )
        if request.search
        else podcasts.order_by("-pub_date")
    )

    return render_pagination_response(
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
@login_required
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
    podcasts = _get_podcasts().subscribed(request.user).filter(private=True).distinct()

    podcasts = (
        podcasts.search(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )
        if request.search
        else podcasts.order_by("-pub_date")
    )

    return render_pagination_response(request, "podcasts/private_feeds.html", podcasts)


@require_form_methods
@login_required
def add_private_feed(
    request: HttpRequest,
) -> HttpResponseRedirect | TemplateResponse:
    """Add new private feed to collection."""
    if request.method == "POST":
        if request.POST.get("action") == "cancel":
            return HttpResponseRedirect(reverse("podcasts:private_feeds"))

        form = PrivateFeedForm(request.POST, user=cast(User, request.user))

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
        form = PrivateFeedForm(user=cast(User, request.user))

    return render_partial_for_target(
        request,
        TemplateResponse(
            request,
            "podcasts/private_feed_form.html",
            {
                "form": form,
            },
        ),
        target="private-feed-form",
        partial="form",
    )


@require_DELETE
@login_required
def remove_private_feed(request: HttpRequest, podcast_id: int) -> HttpResponseRedirect:
    """Removes subscription to private feed."""
    podcast = _get_podcast_or_404(podcast_id, private=True)
    request.user.subscriptions.filter(podcast=podcast).delete()
    messages.info(request, "Removed from Private Feeds")
    return HttpResponseRedirect(reverse("podcasts:private_feeds"))


def _get_podcasts() -> QuerySet[Podcast]:
    return Podcast.objects.published()


def _get_podcast_or_404(podcast_id: int, **kwargs) -> Podcast:
    return get_object_or_404(_get_podcasts(), pk=podcast_id, **kwargs)


def _render_subscribe_action(
    request: HttpRequest, podcast: Podcast, *, is_subscribed: bool
) -> TemplateResponse:
    return TemplateResponse(
        request,
        "podcasts/detail.html#subscribe_button",
        {
            "podcast": podcast,
            "is_subscribed": is_subscribed,
        },
    )
