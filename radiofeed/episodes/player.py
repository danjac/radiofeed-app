from __future__ import annotations

import dataclasses

from django.http import HttpRequest


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
