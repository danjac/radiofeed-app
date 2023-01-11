from __future__ import annotations

import urllib.parse

import httpx

from django.conf import settings
from django.contrib.sites.models import Site
from django.http import HttpRequest
from django.utils import timezone


def build_absolute_uri(url: str = "", request: HttpRequest | None = None) -> str:
    """Returns the full absolute URI based on request or current Site."""
    url = url or "/"

    if request:
        return request.build_absolute_uri(url)

    protocol = "https" if settings.SECURE_SSL_REDIRECT else "http"

    return urllib.parse.urljoin(
        protocol + "://" + Site.objects.get_current().domain, url
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
