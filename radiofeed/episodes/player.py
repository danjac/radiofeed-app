from typing import Optional, TypedDict

from .models import Episode


class PlayerInfo(TypedDict):
    episode: Optional[int]
    current_time: float
    playback_rate: float


def _empty_player_info():
    return PlayerInfo(episode=None, current_time=0, playback_rate=1.0)


class Player:
    """Manages session state of player"""

    def __init__(self, request):
        self.request = request

    def __bool__(self):
        return bool(self.session_data["episode"])

    def start(self, episode, current_time):
        self.session_data = PlayerInfo(
            episode=episode.id, current_time=current_time, playback_rate=1.0
        )

    def is_playing(self, episode):
        return (
            self.request.user.is_authenticated
            and self.session_data["episode"] == episode.id
        )

    def get_episode(self):
        if self.session_data["episode"] is None:
            return None
        return (
            Episode.objects.filter(pk=self.session_data["episode"])
            .select_related("podcast")
            .first()
        )

    def eject(self, mark_completed=False):
        if (episode := self.get_episode()) and mark_completed:
            episode.log_activity(self.request.user, current_time=0, completed=True)
        self.request.session["player"] = _empty_player_info()
        return episode

    def as_dict(self):
        return {
            "episode": self.get_episode(),
            "current_time": self.current_time,
            "playback_rate": self.playback_rate,
        }

    def update(self, current_time, playback_rate):
        self.session_data = PlayerInfo(
            {
                **self.session_data,  # type: ignore
                "current_time": current_time,
                "playback_rate": playback_rate,
            }
        )

    @property
    def current_time(self):
        return self.session_data.get("current_time", 0)

    @current_time.setter
    def current_time(self, current_time):
        self.session_data = {**self.session_data, "current_time": current_time}  # type: ignore

    @property
    def playback_rate(self):
        return self.session_data.get("playback_rate", 1.0)

    @playback_rate.setter
    def playback_rate(self, playback_rate):
        self.session_data = {**self.session_data, "playback_rate": playback_rate}  # type: ignore

    @property
    def session_data(self):
        return self.request.session.setdefault("player", _empty_player_info())

    @session_data.setter
    def session_data(self, player_info):
        self.request.session["player"] = player_info
