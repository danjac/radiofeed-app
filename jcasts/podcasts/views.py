from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ratelimit.decorators import ratelimit

from jcasts.episodes.models import Episode
from jcasts.episodes.views import (
    render_episode_detail_response,
    render_episode_list_response,
)
from jcasts.podcasts import feed_parser, itunes, websub
from jcasts.podcasts.models import Category, Follow, Podcast, Recommendation
from jcasts.shared.decorators import ajax_login_required
from jcasts.shared.pagination import render_paginated_response
from jcasts.shared.response import HttpResponseConflict, HttpResponseNoContent


@require_http_methods(["GET"])
def index(request: HttpRequest) -> HttpResponse:

    follows = (
        set(request.user.follow_set.values_list("podcast", flat=True))
        if request.user.is_authenticated
        else set()
    )
    podcasts = Podcast.objects.published().order_by("-pub_date").distinct()

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


@require_http_methods(["GET"])
def latest(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Redirects to latest episode in podcast."""

    podcast = get_podcast_or_404(request, podcast_id)
    episode = podcast.episode_set.order_by("-pub_date").first()
    return redirect(episode or podcast)


@require_http_methods(["GET"])
def actions(request: HttpRequest, podcast_id: int) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)

    episode = (
        podcast.episode_set.with_current_time(request.user)
        .select_related("podcast")
        .order_by("-pub_date")
        .first()
    )

    if episode is None:
        raise Http404

    return render_episode_detail_response(
        request,
        episode,
        "episodes/_actions.html",
        {"tag": podcast.get_actions_tag()},
    )


@require_http_methods(["GET"])
def search_podcasts(request: HttpRequest) -> HttpResponse:
    if not request.search:
        return redirect("podcasts:index")

    return render_podcast_list_response(
        request,
        Podcast.objects.published()
        .search_or_exact_match(request.search.value)
        .order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        ),
        "podcasts/search.html",
        cached=True,
    )


@ratelimit(key="ip", rate="20/m")
@require_http_methods(["GET"])
def search_itunes(request: HttpRequest) -> HttpResponse:

    feeds = itunes.search_cached(request.search.value) if request.search else []

    return TemplateResponse(
        request,
        "podcasts/itunes_search.html",
        {
            "feeds": feeds,
            "clear_search_url": reverse("podcasts:index"),
        },
    )


@require_http_methods(["GET"])
@cache_page(settings.DEFAULT_CACHE_TIMEOUT)
def search_autocomplete(request: HttpRequest, limit: int = 6) -> HttpResponse:

    if not request.search:
        return HttpResponse()

    podcasts = (
        Podcast.objects.published()
        .search_or_exact_match(request.search.value)
        .order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )[:limit]
    )

    episodes = (
        Episode.objects.search(request.search.value)
        .select_related("podcast")
        .order_by("-rank", "-pub_date")[: limit - len(podcasts)]
    )

    return TemplateResponse(
        request,
        "podcasts/_autocomplete.html",
        {
            "podcasts": podcasts,
            "episodes": episodes,
        },
    )


@require_http_methods(["GET"])
def recommendations(
    request: HttpRequest,
    podcast_id: int,
    slug: str | None = None,
    limit: int = 12,
) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)

    recommendations = (
        Recommendation.objects.filter(podcast=podcast)
        .select_related("recommended")
        .order_by("-similarity", "-frequency")
    )[:limit]

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
def episodes(
    request: HttpRequest, podcast_id: int, slug: str | None = None
) -> HttpResponse:

    podcast = get_podcast_or_404(request, podcast_id)

    newest_first = request.GET.get("ordering", "desc") == "desc"

    episodes = Episode.objects.filter(podcast=podcast).select_related("podcast")

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
def category_detail(request: HttpRequest, category_id: int, slug: str | None = None):

    category = get_object_or_404(Category, pk=category_id)
    podcasts = category.podcast_set.published()

    if request.search:
        podcasts = podcasts.search_or_exact_match(request.search.value).order_by(
            "-exact_match",
            "-rank",
            "-pub_date",
        )

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


@require_http_methods(["GET", "POST"])
@csrf_exempt
def websub_callback(request: HttpRequest, podcast_id: int) -> HttpResponse:

    now = timezone.now()

    if request.method == "POST":
        podcast = get_object_or_404(
            Podcast.objects.active(),
            pk=podcast_id,
            websub_status=Podcast.WebSubStatus.ACTIVE,
        )

        if not websub.check_signature(request, podcast.websub_secret):
            raise Http404("invalid signature")

        feed_parser.parse_podcast_feed.delay(podcast.id)
        return HttpResponseNoContent()

    mode = request.GET.get("hub.mode")
    topic = request.GET.get("hub.topic")
    challenge = request.GET.get("hub.challenge")

    podcast = get_object_or_404(
        Podcast.objects.active(),
        pk=podcast_id,
        websub_mode=mode,
        websub_status=Podcast.WebSubStatus.REQUESTED,
        websub_url=topic,
    )

    if mode == "subscribe":

        try:
            timeout = now + timedelta(seconds=int(request.GET["hub.lease_seconds"]))
        except (KeyError, ValueError):
            raise Http404

        podcast.websub_timeout = timeout
        podcast.websub_status = Podcast.WebSubStatus.ACTIVE
    else:
        podcast.websub_status = Podcast.WebSubStatus.INACTIVE

    podcast.websub_status_changed = now
    podcast.save()

    return HttpResponse(challenge)


def get_podcast_or_404(request: HttpRequest, podcast_id: int) -> Podcast:
    return get_object_or_404(Podcast.objects.published(), pk=podcast_id)


def get_podcast_detail_context(
    request: HttpRequest, podcast: Podcast, extra_context: dict | None = None
) -> dict:

    return {
        "podcast": podcast,
        "num_episodes": Episode.objects.filter(podcast=podcast).count(),
        "has_recommendations": Recommendation.objects.filter(podcast=podcast).exists(),
        "og_data": podcast.get_opengraph_data(request),
        **(extra_context or {}),
    }


def render_follow_response(
    request: HttpRequest, podcast: Podcast, follow: bool
) -> TemplateResponse:

    return TemplateResponse(
        request,
        "podcasts/_follow_toggle.html",
        {"podcast": podcast, "is_following": follow},
    )


def render_podcast_list_response(
    request: HttpRequest,
    podcasts: QuerySet,
    template_name: str,
    extra_context: dict | None = None,
    cached: bool = False,
) -> TemplateResponse:

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
