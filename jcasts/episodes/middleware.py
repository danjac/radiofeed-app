from __future__ import annotations

from typing import ClassVar

from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject

from jcasts.shared.middleware import BaseMiddleware


class Player:
    """Manages current player episode in session"""

    session_key: ClassVar[str] = "player_episode"

    def __init__(self, request: HttpRequest):
        self.request = request

    def get(self) -> str | None:
        return self.request.session.get(self.session_key)

    def set(self, episode_id: int) -> None:
        self.request.session[self.session_key] = episode_id

    def has(self, episode_id: int) -> bool:
        return self.get() == episode_id

    def remove(self) -> int | None:
        return self.request.session.pop(self.session_key, None)


class PlayerMiddleware(BaseMiddleware):
    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.player = SimpleLazyObject(lambda: Player(request))
        return self.get_response(request)
