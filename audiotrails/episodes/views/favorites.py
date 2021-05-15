from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

from audiotrails.shared.decorators import ajax_login_required
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
@ajax_login_required
def add_favorite(request, episode_id):
    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    try:
        Favorite.objects.create(episode=episode, user=request.user)
    except IntegrityError:
        pass

    return render_favorite_toggle(request, episode, True)


@require_POST
@ajax_login_required
def remove_favorite(request, episode_id):
    episode = get_episode_or_404(request, episode_id)

    Favorite.objects.filter(user=request.user, episode=episode).delete()

    return render_favorite_toggle(request, episode, False)


def render_favorite_toggle(request, episode, is_favorited):
    return TemplateResponse(
        request,
        "episodes/_favorite_toggle.html",
        {"episode": episode, "is_favorited": is_favorited},
    )
