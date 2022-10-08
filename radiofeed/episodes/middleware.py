from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject

from radiofeed.common.decorators import middleware
from radiofeed.episodes.player import Player


@middleware
def player_middleware(request: HttpRequest, get_response: Callable) -> HttpResponse:
    """Adds Player instance to request as `request.player`."""
    request.player = SimpleLazyObject(lambda: Player(request))
    return get_response(request)
