from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods

from jcasts.episodes.models import Bookmark
from jcasts.episodes.views import get_episode_or_404
from jcasts.shared.decorators import ajax_login_required
from jcasts.shared.pagination import render_paginated_response
from jcasts.shared.response import HttpResponseConflict, HttpResponseNoContent


@require_http_methods(["GET"])
@login_required
def index(request: HttpRequest) -> HttpResponse:
    favorites = Bookmark.objects.filter(user=request.user).select_related(
        "episode", "episode__podcast"
    )
    if request.search:
        favorites = favorites.search(request.search.value).order_by("-rank", "-created")
    else:
        favorites = favorites.order_by("-created")

    return render_paginated_response(
        request,
        favorites,
        "episodes/favorites.html",
        "episodes/_favorites.html",
    )


@require_http_methods(["POST"])
@ajax_login_required
def add_favorite(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    try:
        Bookmark.objects.create(episode=episode, user=request.user)
        messages.success(request, "Added to Favorites")
        return HttpResponseNoContent()
    except IntegrityError:
        return HttpResponseConflict()


@require_http_methods(["DELETE"])
@ajax_login_required
def remove_favorite(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id)

    Bookmark.objects.filter(user=request.user, episode=episode).delete()

    messages.info(request, "Removed from Favorites")
    return HttpResponseNoContent()
