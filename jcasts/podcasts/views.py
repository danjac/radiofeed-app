import traceback

from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ratelimit.decorators import ratelimit

from jcasts.episodes.views import render_episode_list_response
from jcasts.podcasts import feed_parser, podcastindex, websub
from jcasts.podcasts.models import Category, Follow, Podcast, Recommendation
from jcasts.shared.decorators import ajax_login_required
from jcasts.shared.pagination import render_paginated_response
from jcasts.shared.response import HttpResponseConflict


@require_http_methods(["GET"])
def index(request):

    follows = (
        set(request.user.follow_set.values_list("podcast", flat=True))
        if request.user.is_authenticated
        else set()
    )
    podcasts = (
        Podcast.objects.filter(pub_date__isnull=False).order_by("-pub_date").distinct()
    )

    promoted = "promoted" in request.GET or not follows

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


@require_http_methods(["GET", "POST"])
@csrf_exempt
def websub_subscribe(request, token):

    podcast = get_object_or_404(Podcast, websub_token=token)

    try:

        if request.method == "GET":
            if request.GET["hub.mode"] != "subscribe":
                raise ValueError("hub.mode should be 'subscribe'")

            if request.GET["hub.topic"] != podcast.rss:
                raise ValueError("hub.topic does not match podcast RSS")

            challenge = request.GET["hub.challenge"]
            lease_seconds = int(request.GET["hub.lease_seconds"])

            podcast.websub_requested = None
            podcast.websub_subscribed = timezone.now() + timedelta(
                seconds=lease_seconds
            )
            podcast.save()

            return HttpResponse(challenge)

        websub.validate(request, podcast)
        feed_parser.parse_feed.delay(podcast.rss, force_update=True)
        return HttpResponse()

    except (KeyError, ValueError, websub.Invalid):
        podcast.websub_exception = traceback.format_exc()
        podcast.save()

        raise Http404()


@require_http_methods(["GET"])
def latest(request, podcast_id):
    """Redirects to latest episode in podcast."""

    podcast = get_podcast_or_404(request, podcast_id)
    episode = podcast.episode_set.order_by("-pub_date").first()
    return redirect(episode or podcast.get_absolute_url())


@require_http_methods(["GET"])
def search_podcasts(request):
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
def search_podcastindex(request):

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


@require_http_methods(["GET"])
def podcast_detail(request, podcast_id, slug=None):
    podcast = get_podcast_or_404(request, podcast_id)

    return TemplateResponse(
        request,
        "podcasts/detail.html",
        get_podcast_detail_context(
            request,
            podcast,
            {
                "is_following": podcast.is_following(request.user),
            },
        ),
    )


@require_http_methods(["GET"])
def episodes(request, podcast_id, slug=None):

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
def category_detail(request, category_id, slug=None):

    category = get_object_or_404(Category, pk=category_id)
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
def follow(request, podcast_id):

    podcast = get_podcast_or_404(request, podcast_id)

    try:
        Follow.objects.create(user=request.user, podcast=podcast)
        messages.success(request, "You are now following this podcast")
        return render_follow_response(request, podcast, follow=True)
    except IntegrityError:
        return HttpResponseConflict()


@require_http_methods(["POST"])
@ajax_login_required
def unfollow(request, podcast_id):

    podcast = get_podcast_or_404(request, podcast_id)

    messages.info(request, "You are no longer following this podcast")
    Follow.objects.filter(podcast=podcast, user=request.user).delete()
    return render_follow_response(request, podcast, follow=False)


def get_podcast_or_404(request, podcast_id):
    return get_object_or_404(
        Podcast.objects.filter(pub_date__isnull=False), pk=podcast_id
    )


def get_podcast_detail_context(request, podcast, extra_context=None):

    return {
        "podcast": podcast,
        "has_recommendations": Recommendation.objects.filter(podcast=podcast).exists(),
        "og_data": podcast.get_opengraph_data(request),
        **(extra_context or {}),
    }


def render_follow_response(request, podcast, follow):

    return TemplateResponse(
        request,
        "podcasts/_follow_toggle.html",
        {"podcast": podcast, "is_following": follow},
    )


def render_podcast_list_response(
    request, podcasts, template_name, extra_context=None, cached=False
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
