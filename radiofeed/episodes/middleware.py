from __future__ import annotations

from typing import cast

from django.http import HttpRequest, HttpResponse
from django.utils.functional import SimpleLazyObject

from radiofeed.common.middleware import BaseMiddleware
from radiofeed.episodes.player import Player


class PlayerMiddleware(BaseMiddleware):
    """Adds Player instance to request as `request.player`."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Adds Player instance to request."""
        request.player = cast(Player, SimpleLazyObject(lambda: Player(request)))
        return self.get_response(request)
