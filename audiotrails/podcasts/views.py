from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST, require_safe

from audiotrails.common.decorators import ajax_login_required
from audiotrails.common.pagination import render_paginated_response
from audiotrails.common.types import ContextDict
from audiotrails.episodes.views import render_episode_list_response
from audiotrails.podcasts import itunes
from audiotrails.podcasts.models import Category, Follow, Podcast, Recommendation
from audiotrails.podcasts.tasks import sync_podcast_feed


@require_safe
def index(request: HttpRequest, featured: bool = False) -> HttpResponse:
    follows = (
        list(request.user.follow_set.values_list("podcast", flat=True))
        if request.user.is_authenticated
        else []
    )
    podcasts = (
        Podcast.objects.filter(pub_date__isnull=False).order_by("-pub_date").distinct()
    )

    featured = featured or not follows

    if featured:
        podcasts = podcasts.filter(promoted=True)
    else:
        podcasts = podcasts.filter(pk__in=follows)

    return render_podcast_list_response(
        request,
        podcasts,
        "podcasts/index.html",
        {
            "featured": featured,
            "has_follows": follows,
            "search_url": reverse("podcasts:search_podcasts"),
        },
        cached=featured,
    )


@require_safe
def search_podcasts(request: HttpRequest) -> HttpResponse:
    if not request.search:
        return HttpResponseRedirect(reverse("podcasts:index"))

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


@require_safe
def search_itunes(request: HttpRequest) -> HttpResponse:

    error: bool = False
    results: list[itunes.SearchResult] = []
    new_podcasts: list[Podcast] = []

    if request.search:
        try:
            results, new_podcasts = itunes.search_itunes(request.search)
        except (itunes.Timeout, itunes.Invalid):
            error = True

    for podcast in new_podcasts:
        sync_podcast_feed.delay(rss=podcast.rss)

    return TemplateResponse(
        request,
        "podcasts/itunes_search.html",
        {
            "results": results,
            "error": error,
            "clear_search_url": reverse("podcasts:index"),
        },
    )


@require_safe
@cache_page(60 * 60 * 24)
def cover_image(request: HttpRequest, podcast_id: int, size: int) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)

    return TemplateResponse(
        request,
        "podcasts/_cover_image.html",
        {
            "podcast": podcast,
            "size": size,
            "cover_image": podcast.get_cover_image_thumbnail(),
        },
    )


@require_safe
def preview(request: HttpRequest, podcast_id: int) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)

    return TemplateResponse(
        request,
        "podcasts/_preview.html",
        {
            "podcast": podcast,
            "cover_image": podcast.get_cover_image_thumbnail(),
        },
    )


@require_safe
def recommendations(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)

    recommendations = (
        Recommendation.objects.filter(podcast=podcast)
        .select_related("recommended")
        .order_by("-similarity", "-frequency")
    )[:12]

    return TemplateResponse(
        request,
        "podcasts/recommendations.html",
        get_podcast_detail_context(
            request, podcast, {"recommendations": recommendations}
        ),
    )


@require_safe
def episodes(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)
    newest_first = request.GET.get("ordering", "desc") == "desc"
    oldest_first = not (newest_first)
    show_podcast_detail = newest_first

    episodes = podcast.episode_set.select_related("podcast")

    if request.search:
        episodes = episodes.search(request.search).order_by("-rank", "-pub_date")
        show_podcast_detail = False
    else:
        episodes = episodes.order_by("-pub_date" if newest_first else "pub_date")

    return render_episode_list_response(
        request,
        episodes,
        "podcasts/episodes.html",
        get_podcast_detail_context(
            request,
            podcast,
            {
                "newest_first": newest_first,
                "oldest_first": oldest_first,
                "cover_image": podcast.get_cover_image_thumbnail(),
                "show_podcast_detail": show_podcast_detail,
            },
        ),
        cached=True,
    )


@require_safe
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


@require_safe
def category_detail(
    request: HttpRequest, category_id: int, slug: str | None = None
) -> HttpResponse:
    category: Category = get_object_or_404(
        Category.objects.select_related("parent"), pk=category_id
    )

    podcasts = category.podcast_set.filter(pub_date__isnull=False)

    if request.search:
        podcasts = podcasts.search(request.search).order_by("-rank", "-pub_date")
    else:
        podcasts = podcasts.order_by("-pub_date")

    return render_podcast_list_response(
        request,
        podcasts,
        "podcasts/category_detail.html",
        {
            "category": category,
            "children": category.children.order_by("name"),
        },
        cached=True,
    )


@require_safe
def itunes_category(request: HttpRequest, category_id: int) -> HttpResponse:
    error: bool = False
    results: list[itunes.SearchResult] = []
    new_podcasts: list[Podcast] = []

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
        "podcasts/itunes_category.html",
        {
            "category": category,
            "results": results,
            "error": error,
        },
    )


@ajax_login_required
@require_POST
def follow(request: HttpRequest, podcast_id: int) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)

    try:
        Follow.objects.create(user=request.user, podcast=podcast)
        messages.success(request, "You are now following this podcast")
    except IntegrityError:
        pass
    return render_follow_response(request, podcast, True)


@ajax_login_required
@require_POST
def unfollow(request: HttpRequest, podcast_id: int) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)

    messages.info(request, "You are no longer following this podcast")
    Follow.objects.filter(podcast=podcast, user=request.user).delete()
    return render_follow_response(request, podcast, False)


def get_podcast_or_404(request: HttpRequest, podcast_id: int) -> Podcast:
    return get_object_or_404(Podcast, pk=podcast_id)


def get_podcast_detail_context(
    request: HttpRequest,
    podcast: Podcast,
    extra_context: ContextDict | None = None,
) -> ContextDict:

    return {
        "podcast": podcast,
        "has_recommendations": Recommendation.objects.filter(podcast=podcast).exists(),
        "is_following": podcast.is_following(request.user),
        "og_data": podcast.get_opengraph_data(request),
        **(extra_context or {}),
    }


def render_follow_response(
    request: HttpRequest, podcast: Podcast, is_following: bool
) -> HttpResponse:

    return TemplateResponse(
        request,
        "podcasts/_follow_toggle.html",
        {"podcast": podcast, "is_following": is_following, "action": True},
    )


def render_podcast_list_response(
    request: HttpRequest,
    podcasts: list[Podcast],
    template_name: str,
    extra_context: ContextDict | None = None,
    cached: bool = False,
) -> HttpResponse:

    return render_paginated_response(
        request,
        podcasts,
        template_name,
        pagination_template_name="podcasts/_podcasts_cached.html"
        if cached
        else "podcasts/_podcasts.html",
        extra_context={
            "cache_timeout": settings.DEFAULT_CACHE_TIMEOUT,
            **(extra_context or {}),
        },
    )
