from typing import Final

import httpx
from django.conf import settings

DEFAULT_TIMEOUT: Final = 5


def get_client(
    *,
    headers: dict | None = None,
    follow_redirects: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
    **kwargs,
) -> httpx.Client:
    """Returns HTTP client with default settings."""
    return httpx.Client(
        timeout=timeout,
        follow_redirects=follow_redirects,
        headers={
            "User-Agent": settings.USER_AGENT,
        }
        | (headers or {}),
        **kwargs,
    )
