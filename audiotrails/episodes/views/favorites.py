from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db import IntegrityError
from django.views.decorators.http import require_POST
from turbo_response import Action, TurboStream
from turbo_response.decorators import turbo_stream_response

from audiotrails.shared.pagination import render_paginated_response

from ..models import Favorite
from . import get_episode_or_404


@login_required
def index(request):
    favorites = Favorite.objects.filter(user=request.user).select_related(
        "episode", "episode__podcast"
    )
    if request.search:
        favorites = favorites.search(request.search).order_by("-rank", "-created")
    else:
        favorites = favorites.order_by("-created")

    return render_paginated_response(
        request,
        favorites,
        "episodes/favorites.html",
        "episodes/_favorites.html",
    )


@require_POST
def add_favorite(request, episode_id):
    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    if request.user.is_anonymous:
        return redirect_to_login(episode.get_absolute_url())

    try:
        Favorite.objects.create(episode=episode, user=request.user)
    except IntegrityError:
        pass

    return [
        render_favorite_toggle(request, episode, is_favorited=True),
        TurboStream("favorites")
        .action(
            Action.UPDATE
            if Favorite.objects.filter(user=request.user).count() == 1
            else Action.PREPEND
        )
        .template(
            "episodes/_episode.html",
            {"episode": episode, "dom_id": episode.dom.favorite},
        )
        .render(request=request),
    ]


@require_POST
@turbo_stream_response
def remove_favorite(request, episode_id):
    episode = get_episode_or_404(request, episode_id)

    if request.user.is_anonymous:
        return redirect_to_login(episode.get_absolute_url())

    favorites = Favorite.objects.filter(user=request.user)
    favorites.filter(episode=episode).delete()

    return [
        render_favorite_toggle(request, episode, is_favorited=False),
        TurboStream("favorites").update.render("You have no more Favorites.")
        if favorites.count() == 0
        else TurboStream(episode.dom.favorite).remove.render(),
    ]


def render_favorite_toggle(request, episode, is_favorited):
    return (
        TurboStream(episode.dom.favorite_toggle)
        .replace.template(
            "episodes/_favorite_toggle.html",
            {"episode": episode, "is_favorited": is_favorited},
        )
        .render(request=request)
    )
