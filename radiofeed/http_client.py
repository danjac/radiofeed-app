import functools
from typing import ContextManager

import httpx
from django.conf import settings


class Client:
    """Handles HTTP GET requests."""

    def __init__(
        self,
        headers: dict | None = None,
        *,
        follow_redirects: bool = True,
        timeout: int = 5,
        **kwargs,
    ) -> None:
        headers = {
            "User-Agent": settings.USER_AGENT,
        } | (headers or {})

        self._client = httpx.Client(
            headers=headers,
            follow_redirects=follow_redirects,
            timeout=timeout,
            **kwargs,
        )

    def get(self, url: str, headers: dict | None = None, **kwargs) -> httpx.Response:
        """Does an HTTP GET request."""

        response = self._client.get(url, headers=headers, **kwargs)
        response.raise_for_status()

        return response

    def head(self, url: str, headers: dict | None = None, **kwargs) -> httpx.Response:
        """Does an HTTP HEAD request."""
        response = self._client.head(url, headers=headers, **kwargs)
        response.raise_for_status()

        return response

    def stream(
        self, url: str, headers: dict | None = None, **kwargs
    ) -> ContextManager[httpx.Response]:
        """Does an HTTP GET request and returns a stream."""

        return self._client.stream("GET", url, headers=headers, **kwargs)


@functools.cache
def get_client(**kwargs) -> Client:
    """Returns Client instance"""
    return Client(**kwargs)
