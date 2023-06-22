import http

import requests
from django.contrib import messages
from django.db.models import Exists, OuterRef
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST, require_safe
from django_htmx.http import HttpResponseLocation

from radiofeed.decorators import require_auth, require_form_methods
from radiofeed.episodes.models import Episode
from radiofeed.fragments import render_template_fragments
from radiofeed.pagination import render_paginated_response
from radiofeed.podcasts import itunes
from radiofeed.podcasts.forms import PrivateFeedForm
from radiofeed.podcasts.models import Category, Podcast


@require_safe
def landing_page(request: HttpRequest, limit: int = 30) -> HttpResponse:
    """Render default site home page for anonymous users.

    Redirects authenticated users to podcast index page.
    """
    if request.user.is_authenticated:
        return redirect("podcasts:index")

    return render(
        request,
        "podcasts/landing_page.html",
        {
            "podcasts": Podcast.objects.filter(
                pub_date__isnull=False,
                promoted=True,
            ).order_by("-pub_date")[:limit],
        },
    )


@require_safe
@require_auth
def index(request: HttpRequest) -> HttpResponse:
    """Render default podcast home page for authenticated users."""

    podcasts = Podcast.objects.filter(pub_date__isnull=False).order_by("-pub_date")

    subscribed = podcasts.subscribed(request.user)
    has_subscriptions = subscribed.exists()

    promoted = "promoted" in request.GET or not has_subscriptions
    podcasts = podcasts.filter(promoted=True) if promoted else subscribed

    return render_paginated_response(
        request,
        podcasts,
        "podcasts/index.html",
        {
            "promoted": promoted,
            "has_subscriptions": has_subscriptions,
            "search_url": reverse("podcasts:search_podcasts"),
        },
    )


@require_safe
@require_auth
def search_podcasts(request: HttpRequest) -> HttpResponse:
    """Render search page. Redirects to index page if search is empty."""
    if request.search:
        return render_paginated_response(
            request,
            (
                Podcast.objects.search(request.search.value)
                .filter(pub_date__isnull=False, private=False)
                .order_by(
                    "-exact_match",
                    "-rank",
                    "-pub_date",
                )
            ),
            "podcasts/search.html",
        )

    return redirect("podcasts:index")


@require_auth
@require_safe
def search_itunes(request: HttpRequest) -> HttpResponse:
    """Render iTunes search page. Redirects to index page if search is empty."""
    if request.search:
        feeds: list[itunes.Feed] = []

        try:
            feeds = itunes.search(request.search.value)
        except requests.RequestException:
            messages.error(request, "Sorry, an error occurred trying to access iTunes.")

        return render(
            request,
            "podcasts/itunes_search.html",
            {
                "feeds": feeds,
                "clear_search_url": reverse("podcasts:index"),
            },
        )

    return redirect("podcasts:index")


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
        raise Http404

    return redirect(episode)


@require_safe
@require_auth
def podcast_detail(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:
    """Details for a single podcast."""

    podcast = get_object_or_404(
        Podcast.objects.accessible(request.user),
        pk=podcast_id,
    )

    return render(
        request,
        "podcasts/detail.html",
        {
            "podcast": podcast,
            "is_subscribed": podcast.is_subscribed,
        },
    )


@require_safe
@require_auth
def episodes(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:
    """Render episodes for a single podcast."""
    podcast = get_object_or_404(
        Podcast.objects.accessible(request.user),
        pk=podcast_id,
    )

    episodes = podcast.episodes.select_related("podcast")

    if request.search:
        episodes = episodes.search(request.search.value).order_by("-rank", "-pub_date")
    else:
        episodes = episodes.order_by(
            "-pub_date" if request.ordering.is_desc else "pub_date"
        )

    return render_paginated_response(
        request,
        episodes,
        "podcasts/episodes.html",
        {
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

    podcast = get_object_or_404(Podcast, private=False, pk=podcast_id)

    return render(
        request,
        "podcasts/similar.html",
        {
            "podcast": podcast,
            "recommendations": podcast.recommendations.select_related(
                "recommended"
            ).order_by("-similarity", "-frequency",)[:limit],
        },
    )


@require_safe
@require_auth
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

    podcasts = category.podcasts.filter(
        pub_date__isnull=False, private=False
    ).distinct()

    if request.search:
        podcasts = podcasts.search(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )
    else:
        podcasts = podcasts.order_by("-pub_date")

    return render_paginated_response(
        request,
        podcasts,
        "podcasts/category_detail.html",
        {"category": category},
    )


@require_POST
@require_auth
def subscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Subscribe a user to a podcast. Podcast must be active and public."""
    podcast = get_object_or_404(Podcast, private=False, pk=podcast_id)

    if request.user.subscriptions.filter(podcast=podcast).exists():
        return HttpResponse(status=http.HTTPStatus.CONFLICT)

    request.user.subscriptions.create(podcast=podcast)

    messages.success(request, "You are now subscribed to this podcast")
    return _render_subscribe_action(request, podcast, True)


@require_POST
@require_auth
def unsubscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Unsubscribe user from a podcast."""
    podcast = get_object_or_404(Podcast, private=False, pk=podcast_id)
    request.user.subscriptions.filter(podcast=podcast).delete()
    messages.info(request, "You are no longer subscribed to this podcast")
    return _render_subscribe_action(request, podcast, False)


@require_safe
@require_auth
def private_feeds(request: HttpRequest) -> HttpResponse:
    """Lists user's private feeds."""
    podcasts = Podcast.objects.subscribed(request.user).filter(
        private=True,
        pub_date__isnull=False,
    )

    if request.search:
        podcasts = podcasts.search(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )
    else:
        podcasts = podcasts.order_by("-pub_date")

    return render_paginated_response(
        request,
        podcasts,
        "podcasts/private_feeds.html",
    )


@require_form_methods
@require_auth
def add_private_feed(request: HttpRequest) -> HttpResponse:
    """Add new private feed to collection."""

    form = (
        PrivateFeedForm(request.POST, user=request.user)
        if request.method == "POST"
        else PrivateFeedForm()
    )

    if form.is_valid():
        podcast = form.save()

        message = (
            "Podcast has been added to your private feeds."
            if podcast.pub_date
            else "Podcast should appear in your private feeds in a few minutes."
        )

        messages.success(request, message)

        return HttpResponseLocation(reverse("podcasts:private_feeds"))

    template_name: str = "podcasts/private_feed_form.html"
    context: dict = {"form": form}

    if request.htmx.target == "private-feed-form":
        return render_template_fragments(
            request,
            template_name,
            context,
            use_blocks=["form"],
        )

    return render(request, template_name, context)


@require_POST
@require_auth
def remove_private_feed(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Removes subscription to private feed."""
    podcast = get_object_or_404(Podcast, private=True, pk=podcast_id)
    request.user.subscriptions.filter(podcast=podcast).delete()
    messages.info(request, "Podcast has been removed from your private feeds.")
    return redirect(reverse("podcasts:private_feeds"))


def _render_subscribe_action(
    request: HttpRequest, podcast: Podcast, is_subscribed: bool
) -> HttpResponse:
    return render_template_fragments(
        request,
        "podcasts/detail.html",
        {
            "podcast": podcast,
            "is_subscribed": is_subscribed,
        },
        use_blocks=["subscribe_button", "messages"],
    )
