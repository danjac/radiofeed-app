import hashlib
import hmac
import uuid

from django.http import HttpRequest


class InvalidSignature(ValueError):
    """Raised if bad signature passed in Content Distribution call."""


def check_signature(
    request: HttpRequest, secret: uuid.UUID | None, max_body_size: int = 1024**2
) -> None:
    """Check X-Hub-Signature header against the secret in database.

    Raises:
        InvalidSignature
    """

    if secret is None:
        raise InvalidSignature("secret is not set")

    try:
        content_length = int(request.headers["content-length"])
        algo, signature = request.headers["X-Hub-Signature"].split("=")
    except (KeyError, ValueError) as e:
        raise InvalidSignature("missing or invalid headers") from e

    if content_length > max_body_size:
        raise InvalidSignature("content length exceeds max body size")

    try:
        algo_method = getattr(hashlib, algo)
    except AttributeError as e:
        raise InvalidSignature(f"{algo} is not a valid algorithm") from e

    if not hmac.compare_digest(
        signature,
        hmac.new(
            secret.hex.encode("utf-8"),
            request.body,
            algo_method,
        ).hexdigest(),
    ):
        raise InvalidSignature("signature does not match")
