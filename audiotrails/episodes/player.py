from typing import Optional, TypedDict

from django.utils import timezone

from .models import AudioLog, Episode, QueueItem


class PlayerInfo(TypedDict):
    episode: Optional[int]
    current_time: float
    playback_rate: float


class Player:
    """Manages session state of player"""

    def __init__(self, request):
        self.request = request

    def __bool__(self):
        return bool(self.session_data["episode"])

    def start(self, episode, current_time):
        self.create_audio_log(episode, current_time=current_time)
        self.session_data = PlayerInfo(
            episode=episode.id, current_time=current_time, playback_rate=1.0
        )

    def is_playing(self, episode):
        return (
            self.request.user.is_authenticated
            and self.session_data["episode"] == episode.id
        )

    def get_episode(self):
        if self.session_data["episode"] is None or self.request.user.is_anonymous:
            return None
        return (
            Episode.objects.filter(pk=self.session_data["episode"])
            .select_related("podcast")
            .first()
        )

    def has_next(self):
        if self.request.user.is_authenticated:
            return QueueItem.objects.filter(user=self.request.user).exists()
        return False

    def eject(self, mark_completed=False):
        if (episode := self.get_episode()) and mark_completed:
            self.create_audio_log(episode, current_time=0, completed=True)
        self.request.session["player"] = self.empty_player_info()
        return episode

    def update(self, episode, current_time, playback_rate):
        self.create_audio_log(episode, current_time=current_time)
        self.session_data = PlayerInfo(
            {
                **self.session_data,
                "current_time": current_time,
                "playback_rate": playback_rate,
            }
        )

    def as_dict(self):
        episode = self.get_episode()
        return {
            "episode": episode,
            "current_time": self.current_time,
            "playback_rate": self.playback_rate,
            "has_next": episode and self.has_next(),
        }

    def create_audio_log(
        self,
        episode,
        *,
        current_time=0,
        completed=False,
    ):
        # Updates audio log with current time
        now = timezone.now()
        return AudioLog.objects.update_or_create(
            episode=episode,
            user=self.request.user,
            defaults={
                "updated": now,
                "current_time": current_time or 0,
                "completed": now if completed else None,
            },
        )

    def empty_player_info(self):
        return PlayerInfo(episode=None, current_time=0, playback_rate=1.0)

    @property
    def current_time(self):
        return self.session_data.get("current_time", 0)

    @current_time.setter
    def current_time(self, current_time):
        self.session_data = {**self.session_data, "current_time": current_time}

    @property
    def playback_rate(self):
        return self.session_data.get("playback_rate", 1.0)

    @playback_rate.setter
    def playback_rate(self, playback_rate):
        self.session_data = {**self.session_data, "playback_rate": playback_rate}

    @property
    def session_data(self):
        return self.request.session.setdefault("player", self.empty_player_info())

    @session_data.setter
    def session_data(self, player_info):
        self.request.session["player"] = player_info
