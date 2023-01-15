from __future__ import annotations

import urllib.parse

import httpx

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.signing import BadSignature, Signer
from django.http import HttpRequest
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

_signer = Signer()


def build_absolute_uri(url: str = "", request: HttpRequest | None = None) -> str:
    """Build absolute URI from request, falling back to current Site if unavailable."""
    url = url or "/"

    if request is not None:
        return request.build_absolute_uri(url)

    return urllib.parse.urljoin(
        settings.HTTP_PROTOCOL + "://" + Site.objects.get_current().domain, url
    )


def user_agent(request: HttpRequest | None = None) -> str:
    """Returns user agent including dynamic date-based versioning."""
    return " ".join(
        [
            f"python-httpx/{httpx.__version__}",
            f"(Radiofeed/{timezone.now().strftime('%Y-%d-%m')};",
            f"+{build_absolute_uri(request=request)})",
        ]
    )


def urlsafe_encode(value: str) -> str:
    """Signs and encodes value into URL safe string."""
    return urlsafe_base64_encode(force_bytes(_signer.sign(value)))


def urlsafe_decode(encoded: str) -> str:
    """Decodes value encoded by `urlsafe_encode()`.

    Raises:
        ValueError: bad signature or encoding.
    """
    try:
        return _signer.unsign(force_str(urlsafe_base64_decode(encoded)))
    except BadSignature as e:
        raise ValueError from e
