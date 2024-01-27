from django.http import HttpRequest, HttpResponse

from radiofeed.middleware import BaseMiddleware


class PlayerMiddleware(BaseMiddleware):
    """Adds `Player` instance as `request.player`."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.player = Player(request)
        return self.get_response(request)


class Player:
    """Tracks current player episode in session."""

    session_key: str = "player_episode"
    current_time_key: str = "current_time"

    def __init__(self, request: HttpRequest):
        self.request = request

    def get(self) -> int | None:
        """Returns primary key of episode in player, if any in session."""
        return self.request.session.get(self.session_key)

    def has(self, episode_id: int) -> bool:
        """Checks if episode matching ID is in player."""
        return self.get() == episode_id

    def set(self, episode_id: int, current_time: int) -> None:
        """Adds episode PK to player in session."""
        self.set_current_time(current_time)
        self.request.session[self.session_key] = episode_id

    def pop(self) -> int | None:
        """Returns primary key of episode in player, if any in session, and removes
        the episode ID from the session."""
        self.set_current_time(0)
        return self.request.session.pop(self.session_key, None)

    def get_current_time(self) -> int:
        """Returns the current time in session."""
        try:
            return int(self.request.session.get(self.current_time_key, 0))
        except ValueError:
            return 0

    def set_current_time(self, current_time: int) -> None:
        """Sets the current time in session."""
        self.request.session[self.current_time_key] = current_time
