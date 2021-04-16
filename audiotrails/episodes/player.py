from typing import TypedDict

from django.utils import timezone
from django.utils.functional import cached_property

from .models import AudioLog, QueueItem


class PlayerInfo(TypedDict):
    playback_rate: float


class Player:
    """Manages session state of player"""

    def __init__(self, request):
        self.request = request

    def __bool__(self):
        return self.current_log is not None

    def start(self, episode, current_time):
        self.create_audio_log(episode, current_time=current_time)
        self.session_data = PlayerInfo(playback_rate=1.0)

    def eject(self, mark_completed=False):
        self.request.session["player"] = self.empty_player_info()
        if (log := self.current_log) :

            now = timezone.now()

            log.updated = now
            log.is_playing = False

            if mark_completed:
                log.completed = now
                log.current_time = 0

            log.save()

            episode = log.episode

            # reset cached property
            del self.current_log
            return episode

        return None

    def update(self, episode, current_time, playback_rate):
        self.create_audio_log(episode, current_time=current_time)
        self.session_data = PlayerInfo(playback_rate=playback_rate)

    def is_playing(self, episode):
        if self.request.user.is_anonymous:
            return False
        return self.episode

    def has_next(self):
        if self.request.user.is_authenticated:
            return QueueItem.objects.filter(user=self.request.user).exists()
        return False

    def create_audio_log(
        self,
        episode,
        *,
        current_time=0,
    ):
        # Updates audio log with current time
        now = timezone.now()
        return AudioLog.objects.update_or_create(
            episode=episode,
            user=self.request.user,
            defaults={
                "updated": now,
                "current_time": current_time or 0,
                "is_playing": True,
            },
        )

    def empty_player_info(self):
        return PlayerInfo(playback_rate=1.0)

    @cached_property
    def current_log(self):
        if self.request.user.is_anonymous:
            return None
        return (
            AudioLog.objects.filter(user=self.request.user, is_playing=True)
            .select_related("episode", "episode__podcast")
            .first()
        )

    @property
    def episode(self):
        return self.current_log.episode if self.current_log else None

    @property
    def current_time(self):
        return self.current_log.current_time if self.current_log else 0

    @property
    def playback_rate(self):
        return self.session_data.get("playback_rate", 1.0)

    @playback_rate.setter
    def playback_rate(self, playback_rate):
        self.session_data = PlayerInfo(playback_rate=playback_rate)

    @property
    def session_data(self):
        return self.request.session.setdefault("player", self.empty_player_info())

    @session_data.setter
    def session_data(self, player_info):
        self.request.session["player"] = player_info

    def as_dict(self):
        return {
            "episode": self.episode,
            "current_time": self.current_time,
            "playback_rate": self.playback_rate,
            "has_next": self.episode and self.has_next(),
        }
