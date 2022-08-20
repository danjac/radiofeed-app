from __future__ import annotations

from radiofeed.common.crypto import make_content_hash


class TestMakeContentHash:
    def test_hash_identical(self):
        assert make_content_hash(b"ok") == make_content_hash(b"ok")
