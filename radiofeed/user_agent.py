from __future__ import annotations

import httpx

from django.http import HttpRequest
from django.utils import timezone

from radiofeed.absolute_uri import build_absolute_uri


def user_agent(request: HttpRequest | None = None) -> str:
    """Returns user agent including dynamic date-based versioning."""
    return " ".join(
        [
            f"python-httpx/{httpx.__version__}",
            f"(Radiofeed/{timezone.now().strftime('%Y-%d-%m')};",
            f"+{build_absolute_uri(request=request)})",
        ]
    )
