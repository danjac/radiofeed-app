from django.utils import timezone

from .models import AudioLog


class Player:
    """Tracks current playing episode in user session"""

    session_key = "player_episode"

    def __init__(self, request):
        self.request = request

    def start_episode(self, episode):
        """Creates/updates audio log and adds episode to session.
        Returns current time of episode
        """

        if episode is None:
            return 0

        self.request.session[self.session_key] = episode.id

        log, _ = AudioLog.objects.update_or_create(
            episode=episode,
            user=self.request.user,
            defaults={
                "updated": timezone.now(),
                "completed": None,
            },
        )

        return log.current_time

    def stop_episode(self, mark_completed=False):
        """Removes episode from session and updates log.
        Returns episode.
        """
        if (log := self.get_audio_log()) is None:
            return None

        del self.request.session[self.session_key]

        now = timezone.now()

        log.updated = now

        if mark_completed:
            log.completed = now
            log.current_time = 0

        log.save()

        return log.episode

    def update_current_time(self, current_time):
        if (
            self.request.user.is_authenticated
            and self.session_key in self.request.session
        ):
            AudioLog.objects.filter(
                episode=self.request.session[self.session_key], user=self.request.user
            ).update(current_time=round(current_time))

    def get_player_info(self):
        if log := self.get_audio_log():
            return {
                "current_time": log.current_time,
                "episode": log.episode,
            }
        return {}

    def is_playing(self, episode):
        return self.request.session.get(self.session_key) == episode.id

    def get_audio_log(self):
        if (
            self.request.user.is_anonymous
            or (episode_id := self.request.session.get(self.session_key, None)) is None
        ):
            return None

        return (
            AudioLog.objects.filter(user=self.request.user, episode=episode_id)
            .select_related("episode", "episode__podcast")
            .first()
        )
