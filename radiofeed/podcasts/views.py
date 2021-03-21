from django.conf import settings
from django.db import IntegrityError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST
from turbo_response import TurboFrame, TurboStream

from radiofeed.episodes.views import render_episode_list_response
from radiofeed.pagination import render_paginated_response
from radiofeed.users.decorators import ajax_login_required

from . import itunes
from .models import Category, Follow, Podcast, Recommendation
from .tasks import sync_podcast_feed


def index(request, featured=False):
    follows = (
        list(request.user.follow_set.values_list("podcast", flat=True))
        if request.user.is_authenticated
        else []
    )
    podcasts = (
        Podcast.objects.filter(pub_date__isnull=False).order_by("-pub_date").distinct()
    )

    show_promotions = featured or not follows

    if show_promotions:
        podcasts = podcasts.filter(promoted=True)
    else:
        podcasts = podcasts.filter(pk__in=follows)

    return render_podcast_list_response(
        request,
        podcasts,
        "podcasts/index.html",
        {
            "show_promotions": show_promotions,
            "has_follows": (follows),
            "search_url": reverse("podcasts:search_podcasts"),
        },
        cached=request.user.is_anonymous,
    )


def search_podcasts(request):
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


def search_itunes(request):

    error = False
    results = []
    new_podcasts = []

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


def about(request, podcast_id, slug=None):

    return render_podcast_detail_response(
        request,
        "podcasts/about.html",
        get_podcast_or_404(podcast_id),
    )


def recommendations(request, podcast_id, slug=None):

    podcast = get_podcast_or_404(podcast_id)

    recommendations = (
        Recommendation.objects.filter(podcast=podcast)
        .select_related("recommended")
        .order_by("-similarity", "-frequency")
    )[:12]

    return render_podcast_detail_response(
        request,
        "podcasts/recommendations.html",
        podcast,
        {
            "recommendations": recommendations,
        },
    )


def episodes(request, podcast_id, slug=None):

    podcast = get_podcast_or_404(podcast_id)
    ordering = request.GET.get("ordering")

    episodes = podcast.episode_set.select_related("podcast")

    if request.search:
        episodes = episodes.search(request.search).order_by("-rank", "-pub_date")
    else:
        order_by = "pub_date" if ordering == "asc" else "-pub_date"
        episodes = episodes.order_by(order_by)

    return render_episode_list_response(
        request,
        episodes,
        "podcasts/episodes.html",
        {
            **get_podcast_detail_context(request, podcast),
            "ordering": ordering,
            "cover_image": podcast.get_cover_image_thumbnail(),
            "podcast_url": reverse(
                "podcasts:podcast_detail", args=[podcast.id, podcast.slug]
            ),
        },
        cached=request.user.is_anonymous,
    )


def categories(request):
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


def category_detail(request, category_id, slug=None):
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


def itunes_category(request, category_id):
    error = False
    results = []
    new_podcasts = []

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


@cache_page(60 * 60 * 24)
def podcast_cover_image(request, podcast_id):
    """Lazy-loaded podcast image"""
    podcast = get_podcast_or_404(podcast_id)
    return (
        TurboFrame(request.turbo.frame)
        .template(
            "podcasts/_cover_image.html",
            {
                "podcast": podcast,
                "lazy": False,
                "cover_image": podcast.get_cover_image_thumbnail(),
                "img_size": request.GET.get("size", "16"),
            },
        )
        .response(request)
    )


def preview(request, podcast_id):
    podcast = get_podcast_or_404(podcast_id)

    if request.turbo.frame:
        return (
            TurboFrame(request.turbo.frame)
            .template(
                "podcasts/_preview.html",
                {
                    "podcast": podcast,
                    "is_following": podcast.is_following(request.user),
                },
            )
            .response(request)
        )
    return redirect(podcast.get_absolute_url())


@require_POST
@ajax_login_required
def follow(request, podcast_id):
    podcast = get_podcast_or_404(podcast_id)
    try:
        Follow.objects.create(user=request.user, podcast=podcast)
    except IntegrityError:
        pass
    return render_follow_response(request, podcast, True)


@require_POST
@ajax_login_required
def unfollow(request, podcast_id):
    podcast = get_podcast_or_404(podcast_id)
    Follow.objects.filter(podcast=podcast, user=request.user).delete()
    return render_follow_response(request, podcast, False)


def get_podcast_or_404(podcast_id) -> Podcast:
    return get_object_or_404(Podcast, pk=podcast_id)


def get_podcast_detail_context(
    request,
    podcast,
    extra_context=None,
):

    return {
        "podcast": podcast,
        "has_recommendations": Recommendation.objects.filter(podcast=podcast).exists(),
        "is_following": podcast.is_following(request.user),
        "og_data": podcast.get_opengraph_data(request),
    } | (extra_context or {})


def render_podcast_detail_response(
    request,
    template_name,
    podcast,
    extra_context=None,
):

    return TemplateResponse(
        request,
        template_name,
        get_podcast_detail_context(request, podcast, extra_context),
    )


def render_follow_response(request, podcast, is_following):

    return (
        TurboStream(podcast.dom.follow_toggle)
        .replace.template(
            "podcasts/_follow_toggle.html",
            {"podcast": podcast, "is_following": is_following},
        )
        .response(request=request)
    )


def render_podcast_list_response(
    request,
    podcasts,
    template_name,
    extra_context=None,
    cached=False,
):

    extra_context = extra_context or {}

    if cached:
        extra_context["cache_timeout"] = settings.DEFAULT_CACHE_TIMEOUT
        pagination_template_name = "podcasts/_podcasts_cached.html"
    else:
        pagination_template_name = "podcasts/_podcasts.html"

    return render_paginated_response(
        request, podcasts, template_name, pagination_template_name, extra_context
    )
