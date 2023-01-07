from __future__ import annotations

from django.core.signing import BadSignature, Signer
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

_signer = Signer()


class DecodeError(BadSignature):
    """Any invalid signature."""


def encode(value: str) -> str:
    """Encode value into signed URL-safe encoded string."""
    return urlsafe_base64_encode(force_bytes(_signer.sign(value)))


def decode(encoded: str) -> str:
    """Decode value from an encoded string.

    Raises:
        DecodeError: invalid encoded string
    """
    try:
        return _signer.unsign(force_str(urlsafe_base64_decode(encoded)))
    except (ValueError, BadSignature) as e:
        raise DecodeError from e
