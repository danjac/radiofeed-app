from __future__ import annotations

from django.core.signing import BadSignature, dumps, loads


class DecodeError(BadSignature):
    """Any invalid signature."""


def encode_url(url: str) -> str:
    """Make a random token and store in cache."""
    return dumps({"url": url}, compress=True)


def decode_url(encoded_url: str) -> str:
    """Decode url from an encoded string.

    Raises:
        DecodeError: invalid encoded string
    """
    try:
        return loads(encoded_url)["url"]
    except KeyError:
        raise DecodeError("Invalid signed object")
    except BadSignature as e:
        raise DecodeError from e
