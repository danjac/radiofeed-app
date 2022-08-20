from __future__ import annotations

from radiofeed.feedparser.hasher import hash


class TestMakeContentHash:
    def test_hash_identical(self):
        assert hash(b"ok") == hash(b"ok")
