from django.utils.functional import SimpleLazyObject

from audiotrails.shared.middleware import BaseMiddleware

from .player import Player


class PlayerMiddleware(BaseMiddleware):
    def __call__(self, request):
        request.player = SimpleLazyObject(lambda: Player(request))
        return self.get_response(request)
