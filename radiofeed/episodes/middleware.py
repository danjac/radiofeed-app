# Local
from .models import Episode


class Player:
    """Manages session state of player"""

    def __init__(self, request):
        self.request = request

    def __bool__(self):
        return bool(self.session_data["episode"])

    def start(self, episode, current_time):
        self.session_data = {"episode": episode.id, "current_time": current_time}

    def is_playing(self, episode):
        return self.session_data["episode"] == episode.id

    def get_episode(self):
        if self.session_data["episode"] is None:
            return None
        return (
            Episode.objects.filter(pk=self.session_data["episode"])
            .select_related("podcast")
            .first()
        )

    def get_current_time(self):
        return self.session_data.get("current_time", 0)

    def set_current_time(self, current_time):
        self.session_data = {**self.session_data, "current_time": current_time}

    def clear(self):
        episode = self.get_episode()
        current_time = self.get_current_time()
        self.request.session["player"] = {
            "episode": None,
            "current_time": 0,
        }
        return episode, current_time

    def as_dict(self):
        return {
            "episode": self.get_episode(),
            "current_time": self.get_current_time(),
        }

    @property
    def session_data(self):
        return self.request.session.setdefault(
            "player", {"episode": None, "current_time": 0}
        )

    @session_data.setter
    def session_data(self, data):
        self.request.session["player"] = data


class PlayerSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.player = Player(request)
        return self.get_response(request)
