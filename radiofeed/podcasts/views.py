# Django
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Prefetch
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST

# Third Party Libraries
from turbo_response import TurboFrame, redirect_303

# RadioFeed
from radiofeed.users.decorators import staff_member_required

# Local
from . import itunes
from .forms import PodcastForm
from .models import Category, Podcast, Recommendation, Subscription
from .tasks import sync_podcast_feed


def landing_page(request):
    if request.user.is_authenticated:
        return redirect_303("podcasts:podcast_list")

    podcasts = (
        Podcast.objects.with_subscription_count()
        .filter(pub_date__isnull=False, cover_image__isnull=False, explicit=False)
        .order_by("-subscription_count", "-pub_date")
        .distinct()[:12]
    )

    return TemplateResponse(
        request, "podcasts/landing_page.html", {"podcasts": podcasts}
    )


@cache_page(60 * 60 * 24)
def podcast_cover_image(request, podcast_id):
    """Lazy-loaded podcast image"""
    podcast = get_object_or_404(Podcast, pk=podcast_id)
    return (
        TurboFrame(f"podcast-cover-image-{podcast.id}")
        .template("podcasts/_podcast_cover_image.html", {"podcast": podcast},)
        .response(request)
    )


def podcast_list(request):
    """Shows list of podcasts"""
    podcasts = Podcast.objects.filter(pub_date__isnull=False)
    top_rated_podcasts = False

    if search := request.GET.get("q", None):
        podcasts = podcasts.search(search).order_by("-rank", "-pub_date")
    else:
        subscriptions = (
            list(request.user.subscription_set.values_list("podcast", flat=True))
            if request.user.is_authenticated
            else []
        )
        if subscriptions:
            podcasts = podcasts.filter(pk__in=subscriptions).order_by("-pub_date")
        else:
            podcasts = (
                Podcast.objects.filter(pub_date__isnull=False)
                .with_subscription_count()
                .order_by("-subscription_count", "-pub_date")[
                    : settings.DEFAULT_PAGE_SIZE
                ]
            )
            top_rated_podcasts = True

    return TemplateResponse(
        request,
        "podcasts/index.html",
        {
            "podcasts": podcasts,
            "top_rated_podcasts": top_rated_podcasts,
            "search": search,
        },
    )


def podcast_detail(request, podcast_id, slug=None):
    podcast = get_object_or_404(Podcast, pk=podcast_id)

    total_episodes = podcast.episode_set.count()

    return podcast_detail_response(
        request, "podcasts/detail.html", podcast, {"total_episodes": total_episodes},
    )


def podcast_recommendations(request, podcast_id, slug=None):

    podcast = get_object_or_404(Podcast, pk=podcast_id)

    recommendations = (
        Recommendation.objects.filter(podcast=podcast)
        .select_related("recommended")
        .order_by("-similarity", "-frequency")
    )[:12]

    return podcast_detail_response(
        request,
        "podcasts/recommendations.html",
        podcast,
        {"recommendations": recommendations,},
    )


def podcast_episode_list(request, podcast_id, slug=None):

    podcast = get_object_or_404(Podcast, pk=podcast_id)
    episodes = podcast.episode_set.with_current_time(request.user).select_related(
        "podcast"
    )

    search = request.GET.get("q", None)
    ordering = request.GET.get("ordering")

    if search:
        episodes = episodes.search(search).order_by("-rank", "-pub_date")
    else:
        order_by = "pub_date" if ordering == "asc" else "-pub_date"
        episodes = episodes.order_by(order_by)

    return podcast_detail_response(
        request,
        "podcasts/episodes.html",
        podcast,
        {"episodes": episodes, "search": search, "ordering": ordering,},
    )


def category_list(request):
    categories = Category.objects.all()

    if search := request.GET.get("q", None):
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

    if search := request.GET.get("q", None):
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
    try:
        results = itunes_results_with_podcast(
            itunes.fetch_itunes_genre(category.itunes_genre_id)
        )
        error = False
    except (itunes.Timeout, itunes.Invalid):
        results = []
        error = True

    return TemplateResponse(
        request,
        "podcasts/itunes_category.html",
        {"category": category, "results": results, "error": error,},
    )


def search_itunes(request):

    error = False
    results = []

    if search := request.GET.get("q", None):
        try:
            results = itunes_results_with_podcast(itunes.search_itunes(search))
        except (itunes.Timeout, itunes.Invalid):
            error = True

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
    except IntegrityError:
        pass
    return podcast_subscribe_response(request, podcast, True)


@login_required
@require_POST
def unsubscribe(request, podcast_id):
    podcast = get_object_or_404(Podcast, pk=podcast_id)
    Subscription.objects.filter(podcast=podcast, user=request.user).delete()
    return podcast_subscribe_response(request, podcast, False)


@staff_member_required
@require_POST
def add_podcast(request):
    form = PodcastForm(request.POST)
    if form.is_valid():
        podcast = form.save()
        sync_podcast_feed.delay(podcast_id=podcast.id)
        if request.accept_turbo_stream:
            return (
                TurboFrame("add-podcast")
                .template("podcasts/_add_new_button.html", {"is_added": True},)
                .response(request)
            )
        return redirect_303(podcast)

    return HttpResponseBadRequest()


def itunes_results_with_podcast(results):
    podcasts = Podcast.objects.filter(itunes__in=[r.itunes for r in results]).in_bulk(
        field_name="itunes"
    )
    for result in results:
        result.podcast = podcasts.get(result.itunes, None)
    return results


def podcast_detail_response(request, template_name, podcast, context):
    is_subscribed = (
        request.user.is_authenticated
        and Subscription.objects.filter(podcast=podcast, user=request.user).exists()
    )

    has_recommendations = Recommendation.objects.filter(podcast=podcast).exists()

    context = {
        "podcast": podcast,
        "is_subscribed": is_subscribed,
        "has_recommendations": has_recommendations,
        "og_data": {
            "url": request.build_absolute_uri(podcast.get_absolute_url()),
            "title": f"{request.site.name} | {podcast.title}",
            "description": podcast.description,
            "image": podcast.cover_image.url if podcast.cover_image else None,
        },
    } | context
    return TemplateResponse(request, template_name, context)


def podcast_subscribe_response(request, podcast, is_subscribed):
    if request.accept_turbo_stream:
        return (
            TurboFrame(f"subscribe-{podcast.id}")
            .template(
                "podcasts/_subscribe_buttons.html",
                {"podcast": podcast, "is_subscribed": is_subscribed},
            )
            .response(request)
        )
    return redirect_303(podcast.get_absolute_url())
