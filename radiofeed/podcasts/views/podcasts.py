from typing import List

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page

from turbo_response import TurboFrame

from radiofeed.shortcuts import render_component

from .. import itunes
from ..models import Podcast
from ..tasks import sync_podcast_feed
from . import get_podcast_or_404, render_podcast_list_response


def index(request: HttpRequest) -> HttpResponse:
    subscriptions = (
        list(request.user.subscription_set.values_list("podcast", flat=True))
        if request.user.is_authenticated
        else []
    )
    podcasts = (
        Podcast.objects.filter(pub_date__isnull=False).order_by("-pub_date").distinct()
    )

    if subscriptions:
        podcasts = podcasts.filter(pk__in=subscriptions)
        show_promotions = False
    else:
        podcasts = podcasts.filter(promoted=True)
        show_promotions = True

    return render_podcast_list_response(
        request,
        podcasts,
        "podcasts/index.html",
        {
            "show_promotions": show_promotions,
            "search_url": reverse("podcasts:search_podcasts"),
        },
        cached=request.user.is_anonymous,
    )


def search_podcasts(request: HttpRequest) -> HttpResponse:

    if not request.search:
        return redirect("podcasts:index")

    podcasts = (
        Podcast.objects.filter(pub_date__isnull=False)
        .search(request.search)
        .order_by("-rank", "-pub_date")
    )
    return render_podcast_list_response(
        request,
        podcasts,
        "podcasts/search.html",
        cached=True,
    )


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
    podcast = get_podcast_or_404(podcast_id)
    return TurboFrame(request.turbo.frame).response(
        render_component(
            request,
            "cover_image",
            podcast,
            lazy=False,
            cover_image=podcast.get_cover_image_thumbnail(),
        )
    )
