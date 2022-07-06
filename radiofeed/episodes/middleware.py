from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject

from radiofeed.common.middleware import BaseMiddleware


class Player:
    """Tracks current player episode in session.

    Attributes:
        session_key: session key for current episode id
    """

    session_key: str = "player_episode"

    def __init__(self, request: HttpRequest):
        self._request = request

    def get(self) -> int | None:
        """Returns primary key of episode in player, if any in session."""
        return self._request.session.get(self.session_key)

    def set(self, episode_id: int) -> None:
        """Adds episode PK to player in session."""
        self._request.session[self.session_key] = episode_id

    def has(self, episode_id: int) -> bool:
        """Checks if episode matching ID is in player."""
        return self.get() == episode_id

    def pop(self) -> int | None:
        """Returns primary key of episode in player, if any in session, and removes the episode ID from the session."""
        return self._request.session.pop(self.session_key, None)


class PlayerMiddleware(BaseMiddleware):
    """Adds Player instance to request as `request.player`."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Adds Player instance to request."""
        request.player = SimpleLazyObject(lambda: Player(request))
        return self.get_response(request)
