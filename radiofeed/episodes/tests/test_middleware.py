from __future__ import annotations

from radiofeed.episodes.middleware import PlayerMiddleware


class TestPlayerMiddleware:
    def test_middleware(self, rf, get_response):
        req = rf.get("/")
        PlayerMiddleware(get_response)(req)
        assert req.player
