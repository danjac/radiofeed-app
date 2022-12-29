from __future__ import annotations

import functools

from urllib import parse

import httpx

from django.conf import settings
from django.contrib.sites.models import Site
from django.utils import timezone


def get_absolute_uri(url: str = "/") -> str:
    """Returns the full absolute URI of this site."""
    protocol = "https" if settings.SECURE_SSL_REDIRECT else "http"
    base_url = f"{protocol}://{Site.objects.get_current().domain}"
    return parse.urljoin(base_url, url)


@functools.lru_cache()
def user_agent() -> str:
    """Returns user agent including dynamic date-based versioning."""
    return f"python-httpx/{httpx.__version__} (Radiofeed/{timezone.now().strftime('%Y-%d-%m')}); +{get_absolute_uri()})"
