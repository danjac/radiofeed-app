from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject

from audiotrails.episodes.player import Player
from audiotrails.shared.middleware import BaseMiddleware


class PlayerMiddleware(BaseMiddleware):
    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.player = SimpleLazyObject(lambda: Player(request))
        return self.get_response(request)
