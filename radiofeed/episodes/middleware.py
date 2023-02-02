from __future__ import annotations

import dataclasses

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse


class PlayerMiddleware:
    """Adds `Player` instance as `request.player`."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.player = Player(request)
        return self.get_response(request)


@dataclasses.dataclass(frozen=True)
class Player:
    """Tracks current player episode in session."""

    request: HttpRequest
    session_key: str = "player_episode"

    def __contains__(self, episode_id: int) -> bool:
        """Checks if episode matching ID is in player."""
        return self.get() == episode_id

    def get(self) -> int | None:
        """Returns primary key of episode in player, if any in session."""
        return self.request.session.get(self.session_key)

    def set(self, episode_id: int) -> None:
        """Adds episode PK to player in session."""
        self.request.session[self.session_key] = episode_id

    def pop(self) -> int | None:
        """Returns primary key of episode in player, if any in session, and removes the episode ID from the session."""
        return self.request.session.pop(self.session_key, None)
