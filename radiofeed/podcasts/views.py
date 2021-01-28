# Django
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST

# Third Party Libraries
from sorl.thumbnail import get_thumbnail
from turbo_response import TurboFrame

# RadioFeed
from radiofeed.pagination import paginate
from radiofeed.users.decorators import staff_member_required

# Local
from . import itunes
from .forms import PodcastForm
from .models import Category, Podcast, Recommendation, Subscription
from .tasks import sync_podcast_feed


def landing_page(request):
    if request.user.is_authenticated:
        return redirect("podcasts:podcast_list")

    podcasts = Podcast.objects.filter(
        pub_date__isnull=False,
        cover_image__isnull=False,
        promoted=True,
    ).order_by("-pub_date")[: settings.DEFAULT_PAGE_SIZE]

    return TemplateResponse(
        request, "podcasts/landing_page.html", {"podcasts": podcasts}
    )


def podcast_list(request):
    """Shows list of podcasts"""

    if request.user.is_anonymous or request.search:
        subscriptions = []
    else:
        subscriptions = list(
            request.user.subscription_set.values_list("podcast", flat=True)
        )

    podcasts = Podcast.objects.filter(pub_date__isnull=False)

    if request.search:
        podcasts = podcasts.search(request.search).order_by("-rank", "-pub_date")
    elif subscriptions:
        podcasts = podcasts.filter(pk__in=subscriptions).order_by("-pub_date")
    else:
        podcasts = Podcast.objects.filter(
            pub_date__isnull=False, promoted=True
        ).order_by("-pub_date")[: settings.DEFAULT_PAGE_SIZE]

    context = {
        "page_obj": paginate(request, podcasts),
    }

    if request.turbo.frame:
        return (
            TurboFrame(request.turbo.frame)
            .template(
                "podcasts/_podcast_list.html",
                context,
            )
            .response(request)
        )

    top_rated_podcasts = not (subscriptions) and not (request.search)

    return TemplateResponse(
        request,
        "podcasts/index.html",
        {
            **context,
            "top_rated_podcasts": top_rated_podcasts,
        },
    )


def podcast_detail(request, podcast_id, slug=None):
    podcast = get_object_or_404(Podcast, pk=podcast_id)

    total_episodes = podcast.episode_set.count()

    return podcast_detail_response(
        request,
        "podcasts/detail/detail.html",
        podcast,
        {"total_episodes": total_episodes},
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
        "podcasts/detail/recommendations.html",
        podcast,
        {
            "recommendations": recommendations,
        },
    )


def podcast_episode_list(request, podcast_id, slug=None):

    podcast = get_object_or_404(Podcast, pk=podcast_id)
    ordering = request.GET.get("ordering")

    # thumbnail will be same for all episodes, so just preload
    # it once here
    if podcast.cover_image:
        podcast_image = get_thumbnail(
            podcast.cover_image, "200", format="PNG", crop="center"
        )
    else:
        podcast_image = None

    episodes = podcast.episode_set.with_current_time(request.user).select_related(
        "podcast"
    )

    if request.search:
        episodes = episodes.search(request.search).order_by("-rank", "-pub_date")
    else:
        order_by = "pub_date" if ordering == "asc" else "-pub_date"
        episodes = episodes.order_by(order_by)

    context = {
        "page_obj": paginate(request, episodes),
        "ordering": ordering,
        "podcast_image": podcast_image,
        "podcast_url": reverse(
            "podcasts:podcast_detail", args=[podcast.id, podcast.slug]
        ),
    }

    if request.turbo.frame:

        return (
            TurboFrame(request.turbo.frame)
            .template("episodes/_episode_list.html", context)
            .response(request)
        )

    return podcast_detail_response(
        request, "podcasts/detail/episodes.html", podcast, context
    )


def category_list(request):
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
    category = get_object_or_404(
        Category.objects.select_related("parent"), pk=category_id
    )

    podcasts = category.podcast_set.filter(pub_date__isnull=False)

    if request.search:
        podcasts = podcasts.search(request.search).order_by("-rank", "-pub_date")
    else:
        podcasts = podcasts.order_by("-pub_date")

    context = {"category": category, "page_obj": paginate(request, podcasts)}

    if request.turbo.frame:
        return (
            TurboFrame(request.turbo.frame)
            .template("podcasts/_podcast_list.html", context)
            .response(request)
        )
    else:
        children = category.children.order_by("name")

        return TemplateResponse(
            request,
            "podcasts/category.html",
            {
                "children": children,
            }
            | context,
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
        "podcasts/itunes/category.html",
        {
            "category": category,
            "results": results,
            "error": error,
        },
    )


def search_itunes(request):

    error = False
    results = []

    if request.search:
        try:
            results = itunes_results_with_podcast(itunes.search_itunes(request.search))
        except (itunes.Timeout, itunes.Invalid):
            error = True

    clear_search_url = f"{reverse('podcasts:podcast_list')}?q={request.search}"

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
def subscribe(request, podcast_id):
    podcast = get_object_or_404(Podcast, pk=podcast_id)
    try:
        Subscription.objects.create(user=request.user, podcast=podcast)
    except IntegrityError:
        pass
    return podcast_subscribe_response(request, podcast, True)


@require_POST
@login_required
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
        is_added = True
        is_error = False
    else:
        is_added = False
        is_error = True

    # https://github.com/hotwired/turbo/issues/86
    return (
        TurboFrame(f"add-podcast-{form.cleaned_data['itunes']}")
        .template(
            "podcasts/itunes/_add_new.html",
            {"is_added": is_added, "is_error": is_error},
        )
        .response(request)
    )


@cache_page(60 * 60 * 24)
def podcast_cover_image(request, podcast_id):
    """Lazy-loaded podcast image"""
    podcast = get_object_or_404(Podcast, pk=podcast_id)
    return (
        TurboFrame(request.turbo.frame)
        .template(
            "podcasts/_cover_image.html",
            {"podcast": podcast},
        )
        .response(request)
    )


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
    if request.turbo:
        # https://github.com/hotwired/turbo/issues/86
        return (
            TurboFrame(f"podcast-subscribe-{podcast.id}")
            .template(
                "podcasts/_subscribe.html",
                {"podcast": podcast, "is_subscribed": is_subscribed},
            )
            .response(request)
        )
    return redirect(podcast.get_absolute_url())
