from __future__ import annotations

from django.http import HttpRequest

from radiofeed.common.decorators import lazy_object_middleware
from radiofeed.episodes.player import Player


@lazy_object_middleware("player")
def player_middleware(request: HttpRequest) -> Player:
    """Adds Player instance to request as `request.player`."""
    return Player(request)
