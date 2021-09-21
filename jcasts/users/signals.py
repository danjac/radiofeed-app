from allauth.account.signals import user_logged_in
from django.dispatch import receiver

from jcasts.episodes.models import AudioLog


@receiver(user_logged_in)
def get_last_player_episode(sender, request, **kwargs):
    if (
        log := AudioLog.objects.filter(user=request.user, is_playing=True)
        .order_by("-updated")
        .first()
    ) :
        request.player.set(log.episode_id)
