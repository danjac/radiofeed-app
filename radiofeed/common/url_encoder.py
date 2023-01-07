from __future__ import annotations

from django.core.signing import BadSignature, JSONSerializer, Signer

_signer = Signer()


class DecodeError(BadSignature):
    """Any invalid signature."""


def encode_url(url: str, key: str = "url") -> str:
    """Encode url into signed encoded string."""
    return _signer.sign_object({key: url}, compress=True, serializer=JSONSerializer)


def decode_url(encoded_url: str, key: str = "url") -> str:
    """Decode url from an encoded string.

    Raises:
        DecodeError: invalid encoded string
    """
    try:
        return _signer.unsign_object(encoded_url, serializer=JSONSerializer)[key]
    except KeyError:
        raise DecodeError("Invalid object structure")
    except BadSignature as e:
        raise DecodeError from e
