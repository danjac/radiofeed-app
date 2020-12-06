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
def play_episode(request, episode_id):
    episode = get_object_or_404(
        Episode.objects.select_related("podcast"), pk=episode_id
    )
    # if user logged in, update history in DB
    request.session["player"] = {"episode": episode.id, "current_time": 0}
    return TemplateResponse(request, "episodes/_player.html", {"episode": episode})


@require_POST
def stop_episode(request, episode_id):
    episode = get_object_or_404(Episode, pk=episode_id)
    # if user logged in, update history in DB
    if (
        "player" in request.session
        and request.session["player"]["episode"] == episode.id
    ):
        del request.session["player"]
    return HttpResponse(status=204)


@require_POST
def episode_progress(request, episode_id):
    episode = get_object_or_404(Episode, pk=episode_id)
    if (
        "player" in request.session
        and request.session["player"]["episode"] == episode.id
    ):
        # if user logged in, update history in DB
        request.session["player"]["current_time"] = int(request.POST["current_time"])
    return HttpResponse(status=204)
