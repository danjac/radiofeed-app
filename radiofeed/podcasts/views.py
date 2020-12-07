# Django
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

# Local
from .models import Category, Podcast, Subscription


def podcast_list(request):
    """Shows list of podcasts"""
    podcasts = Podcast.objects.filter(pub_date__isnull=False)

    search = request.GET.get("q", None)

    if search:
        podcasts = podcasts.search(search).order_by("-similarity", "-pub_date")
    else:
        podcasts = podcasts.order_by("-pub_date")

        if request.user.is_authenticated and request.user.subscription_set.exists():
            podcasts = podcasts.filter(subscription__user=request.user).distinct()

    return TemplateResponse(
        request, "podcasts/index.html", {"podcasts": podcasts, "search": search}
    )


def podcast_detail(request, podcast_id, slug=None):
    podcast = get_object_or_404(Podcast, pk=podcast_id)
    episodes = podcast.episode_set.all()

    search = request.GET.get("q", None)

    if search:
        episodes = episodes.search(search).order_by("-similarity", "-pub_date")
    else:
        episodes = episodes.order_by("-pub_date")

    is_subscribed = (
        request.user.is_authenticated
        and Subscription.objects.filter(podcast=podcast, user=request.user).exists()
    )

    return TemplateResponse(
        request,
        "podcasts/detail.html",
        {
            "podcast": podcast,
            "episodes": episodes,
            "search": search,
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
            .prefetch_related("children")
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
    podcasts = category.podcast_set.filter(pub_date__isnull=False)
    search = request.GET.get("q", None)

    if search:
        podcasts = podcasts.search(search).order_by("-similarity", "-pub_date")
    else:
        podcasts = podcasts.order_by("-pub_date")

    return TemplateResponse(
        request,
        "podcasts/category.html",
        {"category": category, "podcasts": podcasts, "search": search,},
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
