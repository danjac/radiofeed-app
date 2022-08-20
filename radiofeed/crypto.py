from __future__ import annotations

import hashlib


def make_content_hash(content: bytes) -> str:
    """Hashes content to a hex string."""
    return hashlib.sha256(content).hexdigest()
