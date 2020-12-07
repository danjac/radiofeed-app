# Standard Library
import json

# Django
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

# Local
from .models import Episode


def episode_list(request):
    episodes = Episode.objects.order_by("-pub_date").select_related("podcast")
    return TemplateResponse(request, "episodes/index.html", {"episodes": episodes})


def episode_detail(request, episode_id, slug=None):
    episode = get_object_or_404(
        Episode.objects.select_related("podcast"), pk=episode_id
    )
    return TemplateResponse(request, "episodes/detail.html", {"episode": episode})


@require_POST
def start_player(request, episode_id):
    """Add episode to session"""
    episode = get_object_or_404(
        Episode.objects.select_related("podcast"), pk=episode_id
    )
    request.session["player"] = {"episode": episode.id, "current_time": 0}
    return TemplateResponse(request, "episodes/_player.html", {"episode": episode})


@require_POST
def stop_player(request):
    """Remove player from session"""
    if "player" in request.session:
        del request.session["player"]
    return HttpResponse(status=204)


@require_POST
def update_player_time(request):
    """Update current play time of episode"""

    if "player" in request.session:
        player = request.session["player"]
        try:
            current_time = int(json.loads(request.body)["current_time"])
        except (json.JSONDecodeError, KeyError):
            current_time = 0
        request.session["player"] = {**player, "current_time": current_time}

    return HttpResponse(status=204)
