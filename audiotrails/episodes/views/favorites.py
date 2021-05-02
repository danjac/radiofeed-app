from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db import IntegrityError
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

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
        messages.success(request, "Episode has been added to your favorites")
    except IntegrityError:
        pass

    return render_toggle_redirect(request, episode)


@require_POST
def remove_favorite(request, episode_id):
    episode = get_episode_or_404(request, episode_id)

    if request.user.is_anonymous:
        return redirect_to_login(episode.get_absolute_url())

    Favorite.objects.filter(user=request.user, episode=episode).delete()

    messages.info(request, "Episode has been removed from your favorites")

    return render_toggle_redirect(request, episode)


def render_toggle_redirect(request, episode):
    if not (
        redirect_url := request.POST.get("redirect_url")
    ) or not url_has_allowed_host_and_scheme(
        redirect_url, {request.get_host()}, require_https=not settings.DEBUG
    ):
        redirect_url = episode.get_absolute_url()

    return redirect(redirect_url)
