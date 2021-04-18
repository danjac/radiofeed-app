from django.utils import timezone

from .models import AudioLog, QueueItem


class Player:
    """Manages session state of player"""

    def __init__(self, request):
        self.request = request

    def __bool__(self):
        return self.current_log is not None

    def start(self, episode):

        self.request.session["player_episode"] = episode.id

        log, _ = AudioLog.objects.update_or_create(
            episode=episode,
            user=self.request.user,
            defaults={
                "updated": timezone.now(),
                "completed": None,
            },
        )
        self._current_log = log

        return log

    def eject(self, mark_completed=False):
        if self.current_log:

            now = timezone.now()

            self.current_log.updated = now

            if mark_completed:
                self.current_log.completed = now
                self.current_log.current_time = 0

            self.current_log.save()

            episode = self.current_log.episode

            del self.request.session["player_episode"]
            self._current_log = None

            return episode

        return None

    def is_playing(self, episode):
        if self.request.user.is_anonymous:
            return False
        return self.episode == episode

    def has_next(self):
        if self.request.user.is_authenticated:
            return QueueItem.objects.filter(user=self.request.user).exists()
        return False

    def get_current_log(self):
        if self.request.user.is_anonymous:
            return None
        if (episode_id := self.request.session.get("player_episode")) is None:
            return None
        return (
            AudioLog.objects.filter(user=self.request.user, episode=episode_id)
            .select_related("episode", "episode__podcast")
            .first()
        )

    @property
    def current_log(self):
        # using this instead  of cached_property for easier resetting
        if hasattr(self, "_current_log"):
            return self._current_log
        self._current_log = self.get_current_log()
        return self._current_log

    @property
    def episode(self):
        return self.current_log.episode if self.current_log else None

    @property
    def current_time(self):
        return self.current_log.current_time if self.current_log else 0

    @current_time.setter
    def current_time(self, current_time):
        if self.current_log:
            self.current_log.current_time = current_time
            self.current_log.save()

    def as_dict(self):
        return {
            "episode": self.episode,
            "current_time": self.current_time,
            "has_next": self.episode and self.has_next(),
        }
