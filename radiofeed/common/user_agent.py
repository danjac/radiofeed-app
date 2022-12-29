from __future__ import annotations

import functools

import httpx

from django.utils import timezone

from radiofeed.common.template import build_absolute_uri


@functools.lru_cache()
def user_agent() -> str:
    """Returns user agent including dynamic date-based versioning."""
    return f"python-httpx/{httpx.__version__} (Radiofeed/{timezone.now().strftime('%Y-%d-%m')}); +{build_absolute_uri()})"
