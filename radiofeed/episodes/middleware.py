from django.utils.functional import SimpleLazyObject

from .player import Player


class PlayerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.player = SimpleLazyObject(lambda: Player(request))
        return self.get_response(request)
