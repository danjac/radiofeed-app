import http
from datetime import timedelta

import requests
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Exists, OuterRef, Q, QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_safe

from radiofeed.decorators import require_auth, require_form_methods
from radiofeed.episodes.models import Episode
from radiofeed.pagination import render_pagination_response
from radiofeed.podcasts import itunes, websub
from radiofeed.podcasts.models import Category, Podcast, Subscription
from radiofeed.users.models import User


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
            "podcasts": _get_podcasts()
            .filter(promoted=True, private=False)
            .order_by("-pub_date")[:limit],
        },
    )


@require_safe
@require_auth
def index(request: HttpRequest) -> HttpResponse:
    """Render default podcast home page for authenticated users."""
    subscribed = _get_subscribed(request.user)
    promoted = "promoted" in request.GET or not subscribed

    podcasts = _get_podcasts().order_by("-pub_date")

    podcasts = (
        podcasts.filter(promoted=True, private=False)
        if promoted
        else podcasts.filter(pk__in=subscribed)
    )

    return render_pagination_response(
        request,
        podcasts,
        "podcasts/index.html",
        "podcasts/_podcasts.html",
        {
            "promoted": promoted,
            "has_subscriptions": bool(subscribed),
            "search_url": reverse("podcasts:search_podcasts"),
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
                _get_podcasts_for_user(request.user)
                .search(request.search.value)
                .order_by(
                    "-exact_match",
                    "-rank",
                    "-pub_date",
                )
            ),
            "podcasts/search.html",
            "podcasts/_podcasts.html",
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
        raise Http404()

    return redirect(episode)


@require_safe
@require_auth
def podcast_detail(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:
    """Details for a single podcast."""

    podcast = get_object_or_404(_get_podcasts_for_user(request.user), pk=podcast_id)

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
    podcast = get_object_or_404(_get_podcasts_for_user(request.user), pk=podcast_id)

    episodes = podcast.episodes.select_related("podcast")

    if request.search:
        episodes = episodes.search(request.search.value).order_by("-rank", "-pub_date")
    else:
        episodes = episodes.order_by(
            "-pub_date" if request.ordering.is_desc else "pub_date"
        )

    return render_pagination_response(
        request,
        episodes,
        "podcasts/episodes.html",
        "episodes/_episodes.html",
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

    podcast = get_object_or_404(_get_podcasts(), pk=podcast_id)

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
                _get_podcasts_for_user(request.user).filter(categories=OuterRef("pk"))
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
    podcasts = (
        _get_podcasts_for_user(request.user).filter(categories=category).distinct()
    )

    if request.search:
        podcasts = podcasts.search(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )
    else:
        podcasts = podcasts.order_by("-pub_date")

    return render_pagination_response(
        request,
        podcasts,
        "podcasts/category_detail.html",
        "podcasts/_podcasts.html",
        {"category": category},
    )


@require_POST
@require_auth
def subscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Subscribe a user to a podcast. Podcast must be active and public.

    Returns:
        returns HTTP CONFLICT if user is already subscribed to this podcast, otherwise
        returns the subscribe action as HTMX snippet.
    """
    podcast = get_object_or_404(_get_podcasts(), private=False, pk=podcast_id)

    try:
        Subscription.objects.create(subscriber=request.user, podcast=podcast)
    except IntegrityError:
        return HttpResponse(status=http.HTTPStatus.CONFLICT)

    messages.success(request, "You are now subscribed to this podcast")
    return _render_subscribe_toggle(request, podcast, True)


@require_POST
@require_auth
def unsubscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Unsubscribe user from a podcast."""
    podcast = get_object_or_404(_get_podcasts(), private=False, pk=podcast_id)

    Subscription.objects.filter(subscriber=request.user, podcast=podcast).delete()

    messages.info(request, "You are no longer subscribed to this podcast")
    return _render_subscribe_toggle(request, podcast, False)


@require_form_methods
@csrf_exempt
@never_cache
def websub_callback(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Callback view as per spec https://www.w3.org/TR/websub/.

    Handles GET and POST requests:

    1. A POST request is used for content distribution and indicates podcast should be updated with new content.

    2. A GET request is used for feed verification.
    """

    podcasts = _get_podcasts().filter(active=True)

    # content distribution
    if request.method == "POST":
        podcast = get_object_or_404(
            podcasts,
            websub_mode="subscribe",
            websub_secret__isnull=False,
            pk=podcast_id,
        )

        try:
            websub.check_signature(request, podcast.websub_secret)

            # queue podast for immediate update
            podcast.queued = timezone.now()
            podcast.save()

        except websub.InvalidSignature as e:
            raise Http404 from e

        return HttpResponse(status=http.HTTPStatus.NO_CONTENT)

    # verification
    try:
        # check all required fields are present

        mode = request.GET["hub.mode"]
        topic = request.GET["hub.topic"]
        challenge = request.GET["hub.challenge"]

        lease_seconds = int(
            request.GET.get("hub.lease_seconds", websub.DEFAULT_LEASE_SECONDS)
        )

        podcast = get_object_or_404(podcasts, rss=topic, pk=podcast_id)

        podcast.websub_mode = mode

        podcast.websub_expires = (
            timezone.now() + timedelta(seconds=lease_seconds)
            if mode == "subscribe"
            else None
        )

        podcast.save()

        return HttpResponse(challenge)

    except (KeyError, ValueError) as e:
        raise Http404 from e


def _get_podcasts() -> QuerySet[Podcast]:
    return Podcast.objects.filter(pub_date__isnull=False)


def _get_podcasts_for_user(user: User) -> QuerySet[Podcast]:
    # get only public podcasts, or those the user is subscribed to
    return _get_podcasts().filter(Q(private=False) | Q(pk__in=_get_subscribed(user)))


def _get_subscribed(user: User) -> set[int]:
    return set(user.subscriptions.values_list("podcast", flat=True))


def _render_subscribe_toggle(
    request: HttpRequest, podcast: Podcast, is_subscribed: bool
) -> HttpResponse:
    if request.htmx:
        return render(
            request,
            "podcasts/_subscribe_toggle.html",
            {
                "podcast": podcast,
                "is_subscribed": is_subscribed,
            },
        )
    return redirect(podcast.get_absolute_url())
