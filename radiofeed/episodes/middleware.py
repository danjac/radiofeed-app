from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject

from radiofeed.typing import HttpCallable

from .player import Player


class PlayerMiddleware:
    def __init__(self, get_response: HttpCallable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.player = SimpleLazyObject(lambda: Player(request))
        return self.get_response(request)
