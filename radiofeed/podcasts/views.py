# Django
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

# Local
from .models import Category, Podcast


def podcast_list(request):
    """Shows list of podcasts"""
    podcasts = Podcast.objects.filter(pub_date__isnull=False)
    search = request.GET.get("q", None)
    if search:
        podcasts = podcasts.search(search).order_by("-similarity", "-pub_date")
    else:
        podcasts = podcasts.order_by("-pub_date")
    return TemplateResponse(
        request, "podcasts/index.html", {"podcasts": podcasts, "search": search}
    )


def podcast_detail(request, podcast_id, slug=None):
    podcast = get_object_or_404(Podcast, pk=podcast_id)
    episodes = podcast.episode_set.order_by("-pub_date")
    return TemplateResponse(
        request, "podcasts/detail.html", {"podcast": podcast, "episodes": episodes}
    )


def category_list(request):
    search = request.GET.get("q", None)
    if search:
        categories = Category.objects.search(search).order_by("-similarity", "name")
    else:
        categories = (
            Category.objects.filter(parent__isnull=True)
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
        {"category": category, "podcasts": podcasts, "search": search},
    )
