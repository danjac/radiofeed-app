from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Prefetch
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from ratelimit.decorators import ratelimit

from jcasts.episodes.views import render_episode_list_response
from jcasts.podcasts import podcastindex
from jcasts.podcasts.models import Category, Follow, Podcast, Recommendation
from jcasts.shared.decorators import ajax_login_required
from jcasts.shared.pagination import render_paginated_response
from jcasts.shared.response import HttpResponseConflict, HttpResponseNoContent
from jcasts.shared.typedefs import ContextDict


@require_http_methods(["GET"])
def index(request: HttpRequest) -> HttpResponse:
    promoted = "promoted" in request.GET

    follows = (
        set(request.user.follow_set.values_list("podcast", flat=True))
        if request.user.is_authenticated
        else set()
    )
    podcasts = (
        Podcast.objects.filter(pub_date__isnull=False).order_by("-pub_date").distinct()
    )

    promoted = promoted or not follows

    if promoted:
        podcasts = podcasts.filter(promoted=True)
    else:
        podcasts = podcasts.filter(pk__in=follows)

    return render_podcast_list_response(
        request,
        podcasts,
        "podcasts/index.html",
        {
            "promoted": promoted,
            "show_latest": True,
            "has_follows": follows,
            "search_url": reverse("podcasts:search_podcasts"),
        },
        cached=promoted,
    )


@require_http_methods(["GET"])
def latest(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Redirects to latest episode in podcast."""

    podcast = get_podcast_or_404(request, podcast_id)
    if (episode := podcast.episode_set.order_by("-pub_date").first()) is None:
        raise Http404()

    return redirect(episode)


@require_http_methods(["GET"])
def search_podcasts(request: HttpRequest) -> HttpResponse:
    if not request.search:
        return redirect("podcasts:index")

    podcasts = (
        Podcast.objects.filter(pub_date__isnull=False)
        .search(request.search.value)
        .order_by("-rank", "-pub_date")
    )

    return render_podcast_list_response(
        request,
        podcasts,
        "podcasts/search.html",
        cached=True,
    )


@ratelimit(key="ip", rate="20/m")
@require_http_methods(["GET"])
def search_podcastindex(request: HttpRequest) -> HttpResponse:

    feeds = podcastindex.search_cached(request.search.value) if request.search else []

    return TemplateResponse(
        request,
        "podcasts/podcastindex_search.html",
        {
            "feeds": feeds,
            "clear_search_url": reverse("podcasts:index"),
        },
    )


@require_http_methods(["GET"])
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


@require_http_methods(["GET"])
def podcast_detail(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:

    return TemplateResponse(
        request,
        "podcasts/detail.html",
        get_podcast_detail_context(
            request,
            get_podcast_or_404(request, podcast_id),
        ),
    )


@require_http_methods(["GET"])
def episodes(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)

    newest_first = request.GET.get("ordering", "desc") == "desc"

    episodes = podcast.episode_set.select_related("podcast")

    if request.search:
        episodes = episodes.search(request.search.value).order_by("-rank", "-pub_date")
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
                "oldest_first": not (newest_first),
                "is_podcast_detail": True,
            },
        ),
        cached=True,
    )


@require_http_methods(["GET"])
def categories(request: HttpRequest) -> HttpResponse:

    categories = Category.objects.all()

    if request.search:
        categories = categories.search(request.search.value).order_by(
            "-similarity", "name"
        )
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


@require_http_methods(["GET"])
def category_detail(
    request: HttpRequest, category_id: int, slug: str | None = None
) -> HttpResponse:
    category: Category = get_object_or_404(
        Category.objects.select_related("parent"), pk=category_id
    )

    podcasts = category.podcast_set.filter(pub_date__isnull=False)

    if request.search:
        podcasts = podcasts.search(request.search.value).order_by("-rank", "-pub_date")
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


@require_http_methods(["POST"])
@ajax_login_required
def follow(request: HttpRequest, podcast_id: int) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)

    try:
        Follow.objects.create(user=request.user, podcast=podcast)
        messages.success(request, "You are now following this podcast")
        return render_follow_response(request, podcast, follow=True)
    except IntegrityError:
        return HttpResponseConflict()


@require_http_methods(["POST"])
@ajax_login_required
def unfollow(request: HttpRequest, podcast_id: int) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)

    messages.info(request, "You are no longer following this podcast")
    Follow.objects.filter(podcast=podcast, user=request.user).delete()
    return render_follow_response(request, podcast, follow=False)


def get_podcast_or_404(request: HttpRequest, podcast_id: int) -> Podcast:
    return get_object_or_404(
        Podcast.objects.filter(pub_date__isnull=False), pk=podcast_id
    )


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
    request: HttpRequest,
    podcast: Podcast,
    follow: bool,
) -> HttpResponse:

    return (
        TemplateResponse(
            request,
            "podcasts/_follow_toggle.html",
            {"podcast": podcast, "is_following": follow},
        )
        if request.POST.get("render")
        else HttpResponseNoContent()
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
