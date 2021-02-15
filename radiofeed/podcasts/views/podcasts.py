from typing import List

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page

from turbo_response import TurboFrame

from .. import itunes
from ..models import Podcast
from ..tasks import sync_podcast_feed
from . import get_podcast_or_404, render_podcast_list


def landing_page(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    podcasts = Podcast.objects.filter(
        pub_date__isnull=False,
        cover_image__isnull=False,
        promoted=True,
    ).order_by("-pub_date")[:12]

    return TemplateResponse(
        request, "podcasts/landing_page.html", {"podcasts": podcasts}
    )


def index(request: HttpRequest) -> HttpResponse:
    """Shows list of podcasts: if user has subscriptions,
    show most recently updated, otherwise show promoted podcasts"""

    subscriptions: List[int]

    if request.user.is_anonymous:
        subscriptions = []
    else:
        subscriptions = list(
            request.user.subscription_set.values_list("podcast", flat=True)
        )

    podcasts = Podcast.objects.filter(pub_date__isnull=False).distinct()

    if subscriptions:
        podcasts = podcasts.filter(pk__in=subscriptions).order_by("-pub_date")

    else:

        podcasts = Podcast.objects.filter(
            pub_date__isnull=False, promoted=True
        ).order_by("-pub_date")

    top_rated_podcasts = not (subscriptions) and not (request.search)

    return render_podcast_list(
        request,
        podcasts,
        "podcasts/index.html",
        {
            "top_rated_podcasts": top_rated_podcasts,
            "search_url": reverse("podcasts:search_podcasts"),
        },
        cached=not (subscriptions),
    )


def search_podcasts(request: HttpRequest) -> HttpResponse:

    if not request.search:
        return redirect("podcasts:index")

    podcasts = (
        Podcast.objects.filter(pub_date__isnull=False)
        .search(request.search)
        .order_by("-rank", "-pub_date")
    )
    return render_podcast_list(
        request,
        podcasts,
        "podcasts/search.html",
        cached=True,
    )


@login_required
def podcast_actions(request: HttpRequest, podcast_id: int) -> HttpResponse:
    podcast = get_podcast_or_404(podcast_id)

    if request.turbo.frame:
        return (
            TurboFrame(request.turbo.frame)
            .template(
                "podcasts/_actions.html",
                {
                    "podcast": podcast,
                    "is_subscribed": podcast.is_subscribed(request.user),
                },
            )
            .response(request)
        )
    return redirect(podcast.get_absolute_url())


def search_itunes(request: HttpRequest) -> HttpResponse:

    error: bool = False
    results: itunes.SearchResultList = []
    new_podcasts: List[Podcast] = []

    if request.search:
        try:
            results, new_podcasts = itunes.search_itunes(request.search)
        except (itunes.Timeout, itunes.Invalid):
            error = True

    for podcast in new_podcasts:
        sync_podcast_feed.delay(rss=podcast.rss)

    clear_search_url = f"{reverse('podcasts:index')}?q={request.search}"

    return TemplateResponse(
        request,
        "podcasts/itunes/search.html",
        {
            "results": results,
            "error": error,
            "clear_search_url": clear_search_url,
        },
    )


@cache_page(60 * 60 * 24)
def podcast_cover_image(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Lazy-loaded podcast image"""
    return (
        TurboFrame(request.turbo.frame)
        .template(
            "podcasts/_cover_image.html",
            {"podcast": get_podcast_or_404(podcast_id)},
        )
        .response(request)
    )
