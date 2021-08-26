from __future__ import annotations

from django.utils.functional import SimpleLazyObject

from jcasts.shared.middleware import BaseMiddleware


class Player:
    """Tracks current player episode in session"""

    session_key = "player_episode"

    def __init__(self, request):
        self.request = request

    def get(self):
        return self.request.session.get(self.session_key)

    def set(self, episode_id):
        self.request.session[self.session_key] = episode_id

    def has(self, episode_id):
        return self.get() == episode_id

    def remove(self):
        return self.request.session.pop(self.session_key, None)


class PlayerMiddleware(BaseMiddleware):
    def __call__(self, request):
        request.player = SimpleLazyObject(lambda: Player(request))
        return self.get_response(request)
