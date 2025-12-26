import dataclasses

from django.http import HttpResponse

from simplecasts.middleware import BaseMiddleware
from simplecasts.request import HttpRequest


class PlayerMiddleware(BaseMiddleware):
    """Adds `PlayerDetails` instance to request as `request.player`."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.player = PlayerDetails(request=request)
        return self.get_response(request)


@dataclasses.dataclass(frozen=True, kw_only=True)
class PlayerDetails:
    """Tracks current player episode in session."""

    request: HttpRequest
    session_id: str = "audio-player"

    def get(self) -> int | None:
        """Returns primary key of episode in player, if any in session."""
        return self.request.session.get(self.session_id)

    def has(self, episode_id: int) -> bool:
        """Checks if episode matching ID is in player."""
        return self.get() == episode_id

    def set(self, episode_id: int) -> None:
        """Adds episode PK to player in session."""
        self.request.session[self.session_id] = episode_id

    def pop(self) -> int | None:
        """Returns primary key of episode in player, if any in session, and removes
        the episode ID from the session."""
        return self.request.session.pop(self.session_id, None)
