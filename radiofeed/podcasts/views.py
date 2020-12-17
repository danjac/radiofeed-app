# Standard Library
import json

# Django
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Prefetch
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

# RadioFeed
from radiofeed.users.decorators import staff_member_required

# Local
from . import itunes
from .forms import PodcastForm
from .models import Category, Podcast, Recommendation, Subscription
from .tasks import sync_podcast_feed


def landing_page(request):
    if request.user.is_authenticated:
        return redirect("podcasts:podcast_list")

    podcasts = (
        Podcast.objects.with_subscription_count()
        .order_by("-subscription_count", "-pub_date")
        .distinct()[:12]
    )

    return TemplateResponse(
        request, "podcasts/landing_page.html", {"podcasts": podcasts}
    )


def podcast_list(request):
    """Shows list of podcasts"""
    podcasts = Podcast.objects.filter(pub_date__isnull=False)

    search = request.GET.get("q", None)

    if search:
        podcasts = podcasts.search(search).order_by("-rank", "-pub_date")
    elif request.user.is_authenticated:
        podcasts = (
            podcasts.with_subscription_count()
            .with_has_subscribed(request.user)
            .order_by("-has_subscribed", "-subscription_count", "-pub_date")
            .distinct()
        )
    else:
        podcasts = podcasts.with_subscription_count().order_by(
            "-subscription_count", "-pub_date"
        )

    return TemplateResponse(
        request, "podcasts/index.html", {"podcasts": podcasts, "search": search}
    )


def podcast_detail(request, podcast_id, slug=None):
    podcast = get_object_or_404(Podcast, pk=podcast_id)
    episodes = podcast.episode_set.with_current_time(request.user)
    total_episodes = episodes.count()

    search = request.GET.get("q", None)
    ordering = request.GET.get("ordering")

    if search:
        episodes = episodes.search(search).order_by("-rank", "-pub_date")
    else:
        order_by = "pub_date" if ordering == "asc" else "-pub_date"
        episodes = episodes.order_by(order_by)

    is_subscribed = (
        request.user.is_authenticated
        and Subscription.objects.filter(podcast=podcast, user=request.user).exists()
    )

    recommendations = (
        Recommendation.objects.filter(podcast=podcast)
        .select_related("recommended")
        .order_by("-similarity", "-frequency")
    )[:9]

    return TemplateResponse(
        request,
        "podcasts/detail.html",
        {
            "podcast": podcast,
            "episodes": episodes,
            "total_episodes": total_episodes,
            "recommendations": recommendations,
            "search": search,
            "ordering": ordering,
            "is_subscribed": is_subscribed,
        },
    )


def category_list(request):
    search = request.GET.get("q", None)
    categories = Category.objects.all()

    if search:
        categories = categories.search(search).order_by("-similarity", "name")
    else:
        categories = (
            categories.filter(parent__isnull=True)
            .prefetch_related(
                Prefetch("children", queryset=Category.objects.order_by("name"),)
            )
            .order_by("name")
        )
    return TemplateResponse(
        request,
        "podcasts/categories.html",
        {"categories": categories, "search": search},
    )


def category_detail(request, category_id, slug=None):
    category = get_object_or_404(
        Category.objects.select_related("parent"), pk=category_id
    )
    children = category.children.order_by("name")

    podcasts = category.podcast_set.filter(pub_date__isnull=False)
    search = request.GET.get("q", None)

    if search:
        podcasts = podcasts.search(search).order_by("-rank", "-pub_date")
    else:
        podcasts = podcasts.order_by("-pub_date")

    return TemplateResponse(
        request,
        "podcasts/category.html",
        {
            "category": category,
            "children": children,
            "podcasts": podcasts,
            "search": search,
        },
    )


def itunes_category(request, category_id):
    category = get_object_or_404(
        Category.objects.select_related("parent").filter(itunes_genre_id__isnull=False),
        pk=category_id,
    )
    error = False
    results = []
    try:
        results = itunes.fetch_itunes_genre(category.itunes_genre_id)
    except (itunes.Timeout, itunes.Invalid):
        error = True

    results = itunes_results_with_podcast(results)

    return TemplateResponse(
        request,
        "podcasts/itunes_category.html",
        {"category": category, "results": results, "error": error,},
    )


def search_itunes(request):
    search = request.GET.get("q", None)
    error = False
    results = []

    if search:
        try:
            results = itunes.search_itunes(search)
        except (itunes.Timeout, itunes.Invalid):
            error = True

    results = itunes_results_with_podcast(results)

    clear_search_url = f"{reverse('podcasts:podcast_list')}?q={search}"

    return TemplateResponse(
        request,
        "podcasts/itunes.html",
        {
            "results": results,
            "error": error,
            "search": search,
            "clear_search_url": clear_search_url,
        },
    )


@login_required
@require_POST
def subscribe(request, podcast_id):
    podcast = get_object_or_404(Podcast, pk=podcast_id)
    try:
        Subscription.objects.create(user=request.user, podcast=podcast)
        messages.success(request, "You are now subscribed to this podcast")
    except IntegrityError:
        pass
    return redirect(podcast.get_absolute_url())


@login_required
@require_POST
def unsubscribe(request, podcast_id):
    podcast = get_object_or_404(Podcast, pk=podcast_id)
    Subscription.objects.filter(podcast=podcast, user=request.user).delete()
    messages.info(request, "You are no longer subscribed to this podcast")
    return redirect(podcast.get_absolute_url())


@staff_member_required
@require_POST
def add_podcast(request):
    form = PodcastForm(json.loads(request.body))
    if form.is_valid():
        podcast = form.save()
        sync_podcast_feed.delay(podcast_id=podcast.id)
        return JsonResponse({"id": podcast.id, "title": podcast.title})

    return HttpResponseBadRequest()


def itunes_results_with_podcast(results):
    podcasts = Podcast.objects.filter(rss__in=[r.rss for r in results]).in_bulk(
        field_name="rss"
    )
    for result in results:
        result.podcast = podcasts.get(result.rss, None)
    return results
