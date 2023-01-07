from __future__ import annotations

import functools

from django.core.signing import BadSignature, Signer
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

_signer = Signer()


class DecodeError(BadSignature):
    """Any invalid signature."""


@functools.lru_cache
def encode_url(url: str) -> str:
    """Encode url into signed encoded string."""
    return urlsafe_base64_encode(force_bytes(_signer.sign(url)))


@functools.lru_cache
def decode_url(encoded_url: str) -> str:
    """Decode url from an encoded string.

    Raises:
        DecodeError: invalid encoded string
    """
    try:
        return _signer.unsign(force_str(urlsafe_base64_decode(encoded_url)))
    except (ValueError, BadSignature) as e:
        raise DecodeError from e
