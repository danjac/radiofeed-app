from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject

from audiotrails.common.middleware import BaseMiddleware
from audiotrails.episodes.player import Player


class PlayerMiddleware(BaseMiddleware):
    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.player = SimpleLazyObject(lambda: Player(request))
        return self.get_response(request)
