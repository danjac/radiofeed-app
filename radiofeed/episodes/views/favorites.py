from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

from turbo_response import TurboStream

from radiofeed.pagination import render_paginated_response

from ..models import Episode, Favorite
from . import get_episode_or_404


@login_required
def index(request: HttpRequest) -> HttpResponse:
    if request.turbo.frame:
        favorites = Favorite.objects.filter(user=request.user).select_related(
            "episode", "episode__podcast"
        )
        if request.search:
            favorites = favorites.search(request.search).order_by("-rank", "-created")
        else:
            favorites = favorites.order_by("-created")

        return render_paginated_response(
            request, favorites, "episodes/favorites/_episode_list.html"
        )

    return TemplateResponse(request, "episodes/favorites/index.html")


@require_POST
@login_required
def add_favorite(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(episode_id)

    try:
        Favorite.objects.create(episode=episode, user=request.user)
    except IntegrityError:
        pass
    return render_favorite_response(request, episode, True)


@require_POST
@login_required
def remove_favorite(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(episode_id)

    favorites = Favorite.objects.filter(user=request.user)
    favorites.filter(episode=episode).delete()

    if "remove" in request.POST:
        if favorites.count() == 0:
            return TurboStream("favorites").replace.response(
                "There are no more episodes in your Favorites."
            )
        return TurboStream(episode.get_favorite_dom_id()).remove.response()

    return render_favorite_response(request, episode, False)


def render_favorite_response(
    request: HttpRequest, episode: Episode, is_favorited: bool
) -> HttpResponse:
    return (
        TurboStream(episode.get_favorite_toggle_id())
        .replace.template(
            "episodes/favorites/_toggle.html",
            {"episode": episode, "is_favorited": is_favorited},
        )
        .response(request)
    )
