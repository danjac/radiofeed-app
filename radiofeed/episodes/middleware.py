from __future__ import annotations

from radiofeed.decorators import lazy_object_middleware
from radiofeed.episodes.player import Player

player_middleware = lazy_object_middleware("player")(Player)
