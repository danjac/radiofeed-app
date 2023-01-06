from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject

from radiofeed.common.decorators import middleware
from radiofeed.common.types import GetResponse
from radiofeed.episodes.player import Player


@middleware
def player_middleware(request: HttpRequest, get_response: GetResponse) -> HttpResponse:
    """Adds Player instance to request as `request.player`."""
    request.player = SimpleLazyObject(lambda: Player(request))
    return get_response(request)
