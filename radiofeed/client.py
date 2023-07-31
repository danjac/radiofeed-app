import httpx
from django.conf import settings


def http_client(
    *, headers: dict | None = None, timeout: int = 10, **kwargs
) -> httpx.Client:
    """Returns HTTP client instance"""
    return httpx.Client(
        headers={"User-Agent": settings.USER_AGENT, **(headers or {})},
        timeout=timeout,
        **kwargs,
    )
