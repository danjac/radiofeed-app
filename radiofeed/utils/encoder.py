from __future__ import annotations

from django.core.signing import BadSignature, Signer
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

_signer = Signer()


def encode(value: str) -> str:
    """Signs and encodes value into URL safe string."""
    return urlsafe_base64_encode(force_bytes(_signer.sign(value)))


def decode(encoded: str) -> str:
    """Decodes value encoded by `encode()`.

    Raises:
        ValueError: bad signature or encoding.
    """
    try:
        return _signer.unsign(force_str(urlsafe_base64_decode(encoded)))
    except BadSignature as e:
        raise ValueError from e
