from __future__ import annotations

from radiofeed.episodes.middleware.player import Player
from radiofeed.middleware import lazy_object_middleware

player_middleware = lazy_object_middleware(Player, "player")
