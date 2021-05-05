from django.utils import timezone

from .models import AudioLog, QueueItem


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

        QueueItem.objects.filter(user=self.request.user, episode=episode).delete()

        log, _ = AudioLog.objects.update_or_create(
            episode=episode,
            user=self.request.user,
            defaults={
                "updated": timezone.now(),
                "completed": None,
            },
        )

        self.current_log = log

        return log

    def stop_episode(self, mark_completed=False):
        """Removes episode from session and updates log.
        Returns episode.
        """
        if (log := self.get_audio_log()) is None:
            return None

        del self.request.session[self.session_key]

        self.current_log = None

        now = timezone.now()

        log.updated = now

        if mark_completed:
            log.completed = now
            log.current_time = 0

        log.save()

        return log

    def update_current_time(self, current_time):
        if (
            self.request.user.is_authenticated
            and self.session_key in self.request.session
        ):
            AudioLog.objects.filter(
                episode=self.request.session[self.session_key], user=self.request.user
            ).update(current_time=round(current_time))

    def is_playing(self, episode):
        return self.request.session.get(self.session_key) == episode.id

    def get_audio_log(self):
        if hasattr(self, "current_log"):
            return self.current_log
        if (
            self.request.user.is_anonymous
            or (episode_id := self.request.session.get(self.session_key, None)) is None
        ):
            self.current_log = None

        self.current_log = (
            AudioLog.objects.filter(user=self.request.user, episode=episode_id)
            .select_related("episode", "episode__podcast")
            .first()
        )
        return self.current_log
