from __future__ import annotations

from django.core.signing import BadSignature, dumps, loads


class DecodeError(BadSignature):
    """Any invalid signature."""


def encode_url(url: str) -> str:
    """Return encoded string from a URL."""
    return dumps({"url": url}, compress=True)


def decode_url(encoded: str) -> str:
    """Decode url from an encoded string.

    Raises:
        DecodeError: invalid encoded string
    """
    try:
        return loads(encoded)["url"]
    except (KeyError, BadSignature) as e:
        raise DecodeError from e
