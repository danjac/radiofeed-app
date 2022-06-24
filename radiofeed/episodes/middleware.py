from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject

from radiofeed.common.middleware import BaseMiddleware


class Player:
    """Tracks current player episode in session"""

    session_key = "player_episode"

    def __init__(self, request: HttpRequest):
        self.request = request

    def get(self) -> int | None:
        return self.request.session.get(self.session_key)

    def set(self, episode_id: int) -> None:
        self.request.session[self.session_key] = episode_id

    def has(self, episode_id: int) -> bool:
        return self.get() == episode_id

    def pop(self) -> int | None:
        return self.request.session.pop(self.session_key, None)


class PlayerMiddleware(BaseMiddleware):
    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.player = SimpleLazyObject(lambda: Player(request))
        return self.get_response(request)
