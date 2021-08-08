from __future__ import annotations

from typing import ClassVar

from django.http import HttpRequest

from jcasts.episodes.models import Episode


class Player:
    session_key: ClassVar[str] = "player_episode"

    def __init__(self, request: HttpRequest):
        self.request = request

    def get_episode(self) -> str | None:
        return self.request.session.get(self.session_key)

    def add_episode(self, episode: Episode) -> None:
        self.request.session[self.session_key] = episode.id

    def remove_episode(self) -> str | None:
        return self.request.session.pop(self.session_key, None)

    def is_playing(self, episode: Episode) -> bool:
        return self.get_episode() == episode.id
