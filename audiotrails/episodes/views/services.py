from django.contrib.auth.views import redirect_to_login
from django.shortcuts import get_object_or_404

from audiotrails.middleware import RedirectException

from ..models import AudioLog, Episode, Favorite, QueueItem


def get_episode_or_404(
    request,
    episode_id,
    *,
    with_podcast=False,
    with_current_time=False,
    auth_required=False,
):
    qs = Episode.objects.all()
    if with_podcast:
        qs = qs.select_related("podcast")
    if with_current_time:
        qs = qs.with_current_time(request.user)
    episode = get_object_or_404(qs, pk=episode_id)
    if auth_required and not request.user.is_authenticated:
        raise RedirectException(redirect_to_login(episode.get_absolute_url()))
    return episode


def get_episode_detail_context(request, episode, extra_context=None):
    return {
        "episode": episode,
        "is_playing": request.player.is_playing(episode),
        "is_favorited": episode.is_favorited(request.user),
        "is_queued": episode.is_queued(request.user),
        **(extra_context or {}),
    }


def get_audio_logs(request):
    return AudioLog.objects.filter(user=request.user)


def get_favorites(request):
    return Favorite.objects.filter(user=request.user)


def get_queue_items(request):
    return QueueItem.objects.filter(user=request.user)


def delete_queue_item(request, episode):
    items = get_queue_items(request)
    items.filter(episode=episode).delete()
    return items.exists()
