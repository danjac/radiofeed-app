from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.db import IntegrityError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

from audiotrails.episodes.views import render_episode_list_response
from audiotrails.shared.pagination import render_paginated_response

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


def recommendations(request, podcast_id, slug=None):

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


def episodes(request, podcast_id, slug=None):

    podcast = get_podcast_or_404(request, podcast_id)
    newest_first = request.GET.get("ordering", "desc") == "desc"
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
                "show_podcast_detail": show_podcast_detail,
                "cover_image": podcast.get_cover_image_thumbnail(),
            },
        ),
        cached=True,
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


@require_POST
def follow(request, podcast_id):

    podcast = get_podcast_or_404(request, podcast_id)

    if request.user.is_anonymous:
        return redirect_to_login(podcast.get_absolute_url())

    try:
        Follow.objects.create(user=request.user, podcast=podcast)
    except IntegrityError:
        pass
    return render_follow_response(request, podcast, True)


@require_POST
def unfollow(request, podcast_id):

    podcast = get_podcast_or_404(request, podcast_id)

    if request.user.is_anonymous:
        return redirect_to_login(podcast.get_absolute_url())

    Follow.objects.filter(podcast=podcast, user=request.user).delete()
    return render_follow_response(request, podcast, False)


def get_podcast_or_404(request, podcast_id):
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
        **(extra_context or {}),
    }


def render_follow_response(request, podcast, is_following):

    return TemplateResponse(
        request,
        "podcasts/_follow_toggle.html",
        {"podcast": podcast, "is_following": is_following},
    )


def render_podcast_list_response(
    request,
    podcasts,
    template_name,
    extra_context=None,
    cached=False,
):

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
