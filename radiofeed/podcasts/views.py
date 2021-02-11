from typing import Dict, List, Optional

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST

from turbo_response import TurboFrame, TurboStream

from radiofeed.pagination import render_paginated_response

from . import itunes
from .models import Category, Podcast, Recommendation, Subscription
from .tasks import sync_podcast_feed


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


def podcasts(request: HttpRequest) -> HttpResponse:
    """Shows list of podcasts: if user has subscriptions,
    show most recently updated, otherwise show promoted podcasts"""

    subscriptions: List[int]

    if request.user.is_anonymous:
        subscriptions = []
    else:
        subscriptions = list(
            request.user.subscription_set.values_list("podcast", flat=True)
        )

    if request.turbo.frame:
        podcasts = Podcast.objects.filter(pub_date__isnull=False).distinct()

        # user's subscribed podcasts

        if subscriptions:
            podcasts = podcasts.filter(pk__in=subscriptions).order_by("-pub_date")

            return render_paginated_response(
                request,
                podcasts,
                "podcasts/_podcast_list.html",
            )

        # return promoted list, same as landing_page

        podcasts = Podcast.objects.filter(
            pub_date__isnull=False, promoted=True
        ).order_by("-pub_date")

        return render_paginated_response(
            request,
            podcasts,
            "podcasts/_podcast_list_cached.html",
            {"cache_timeout": settings.DEFAULT_CACHE_TIMEOUT},
        )

    top_rated_podcasts = not (subscriptions) and not (request.search)

    return TemplateResponse(
        request,
        "podcasts/index.html",
        {
            "top_rated_podcasts": top_rated_podcasts,
            "search_url": reverse("podcasts:search_podcasts"),
        },
    )


def search_podcasts(request: HttpRequest) -> HttpResponse:

    if not request.search:
        return redirect("podcasts:index")

    if request.turbo.frame:
        podcasts = (
            Podcast.objects.filter(pub_date__isnull=False)
            .search(request.search)
            .order_by("-rank", "-pub_date")
        )
        return render_paginated_response(
            request,
            podcasts,
            "podcasts/_podcast_list_cached.html",
            {"cache_timeout": settings.DEFAULT_CACHE_TIMEOUT},
        )

    return TemplateResponse(request, "podcasts/search.html")


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


def podcast_detail(
    request: HttpRequest, podcast_id: int, slug: Optional[str] = None
) -> HttpResponse:
    podcast = get_podcast_or_404(podcast_id)

    total_episodes: int = podcast.episode_set.count()

    return render_podcast_detail_response(
        request,
        "podcasts/detail/detail.html",
        podcast,
        {"total_episodes": total_episodes},
    )


def podcast_recommendations(
    request: HttpRequest, podcast_id: int, slug: Optional[str] = None
) -> HttpResponse:

    podcast = get_podcast_or_404(podcast_id)

    recommendations = (
        Recommendation.objects.filter(podcast=podcast)
        .select_related("recommended")
        .order_by("-similarity", "-frequency")
    )[:12]

    return render_podcast_detail_response(
        request,
        "podcasts/detail/recommendations.html",
        podcast,
        {
            "recommendations": recommendations,
        },
    )


def podcast_episodes(
    request: HttpRequest, podcast_id: int, slug: Optional[str] = None
) -> HttpResponse:

    podcast = get_podcast_or_404(podcast_id)
    ordering: Optional[str] = request.GET.get("ordering")

    if request.turbo.frame:

        # thumbnail will be same for all episodes, so just preload
        # it once here

        episodes = podcast.episode_set.select_related("podcast")

        if request.search:
            episodes = episodes.search(request.search).order_by("-rank", "-pub_date")
        else:
            order_by = "pub_date" if ordering == "asc" else "-pub_date"
            episodes = episodes.order_by(order_by)

        return render_paginated_response(
            request,
            episodes,
            "episodes/_episode_list_cached.html",
            {
                "cache_timeout": settings.DEFAULT_CACHE_TIMEOUT,
                "podcast_image": podcast.get_cover_image_thumbnail(),
                "podcast_url": reverse(
                    "podcasts:podcast_detail", args=[podcast.id, podcast.slug]
                ),
            },
        )

    return render_podcast_detail_response(
        request,
        "podcasts/detail/episodes.html",
        podcast,
        {
            "ordering": ordering,
        },
    )


def categories(request: HttpRequest) -> HttpResponse:
    categories = Category.objects.all()

    if request.search:
        categories = categories.search(request.search).order_by("-similarity", "name")
    else:
        categories = (
            categories.filter(parent__isnull=True)
            .prefetch_related(
                Prefetch(
                    "children",
                    queryset=Category.objects.order_by("name"),
                )
            )
            .order_by("name")
        )
    return TemplateResponse(
        request,
        "podcasts/categories.html",
        {"categories": categories},
    )


def category_detail(request: HttpRequest, category_id: int, slug: Optional[str] = None):
    category: Category = get_object_or_404(
        Category.objects.select_related("parent"), pk=category_id
    )

    if request.turbo.frame:

        podcasts = category.podcast_set.filter(pub_date__isnull=False)

        if request.search:
            podcasts = podcasts.search(request.search).order_by("-rank", "-pub_date")
        else:
            podcasts = podcasts.order_by("-pub_date")

        return render_paginated_response(
            request,
            podcasts,
            "podcasts/_podcast_list_cached.html",
            {"cache_timeout": settings.DEFAULT_CACHE_TIMEOUT},
        )

    return TemplateResponse(
        request,
        "podcasts/category.html",
        {"category": category, "children": category.children.order_by("name")},
    )


def itunes_category(request: HttpRequest, category_id: int) -> HttpResponse:
    error: bool = False
    results: itunes.SearchResultList = []
    new_podcasts: List[Podcast] = []

    category = get_object_or_404(
        Category.objects.select_related("parent").filter(itunes_genre_id__isnull=False),
        pk=category_id,
    )
    try:
        results, new_podcasts = itunes.fetch_itunes_genre(category.itunes_genre_id)
        error = False
    except (itunes.Timeout, itunes.Invalid):
        error = True

    for podcast in new_podcasts:
        sync_podcast_feed.delay(rss=podcast.rss)

    return TemplateResponse(
        request,
        "podcasts/itunes/category.html",
        {
            "category": category,
            "results": results,
            "error": error,
        },
    )


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


@require_POST
@login_required
def subscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:
    podcast = get_podcast_or_404(podcast_id)
    try:
        Subscription.objects.create(user=request.user, podcast=podcast)
    except IntegrityError:
        pass
    return render_podcast_subscribe_response(request, podcast, True)


@require_POST
@login_required
def unsubscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:
    podcast = get_podcast_or_404(podcast_id)
    Subscription.objects.filter(podcast=podcast, user=request.user).delete()
    return render_podcast_subscribe_response(request, podcast, False)


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


def get_podcast_or_404(podcast_id: int) -> Podcast:
    return get_object_or_404(Podcast, pk=podcast_id)


def get_podcast_detail_context(
    request: HttpRequest,
    podcast: Podcast,
    extra_context: Optional[Dict] = None,
) -> Dict:

    return {
        "podcast": podcast,
        "has_recommendations": Recommendation.objects.filter(podcast=podcast).exists(),
        "is_subscribed": podcast.is_subscribed(request.user),
        "og_data": podcast.get_opengraph_data(request),
    } | (extra_context or {})


def render_podcast_detail_response(
    request: HttpRequest,
    template_name: str,
    podcast: Podcast,
    extra_context: Optional[Dict] = None,
) -> HttpResponse:

    return TemplateResponse(
        request,
        template_name,
        get_podcast_detail_context(request, podcast, extra_context),
    )


def render_podcast_subscribe_response(
    request: HttpRequest, podcast: Podcast, is_subscribed: bool
) -> HttpResponse:
    if request.turbo:
        return (
            TurboStream(podcast.get_subscribe_toggle_id())
            .replace.template(
                "podcasts/_subscribe.html",
                {"podcast": podcast, "is_subscribed": is_subscribed},
            )
            .response(request)
        )
    return redirect(podcast.get_absolute_url())
