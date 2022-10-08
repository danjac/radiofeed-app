from __future__ import annotations

from radiofeed.episodes.middleware import player_middleware


class TestPlayerMiddleware:
    def test_middleware(self, rf, get_response):
        req = rf.get("/")
        player_middleware(get_response)(req)
        assert req.player
