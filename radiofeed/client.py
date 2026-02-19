import contextlib
from typing import TYPE_CHECKING

import httpx
from django.conf import settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


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

        self._client = httpx.AsyncClient(
            headers=headers,
            follow_redirects=follow_redirects,
            timeout=timeout,
            **kwargs,
        )

    async def get(
        self, url: str, headers: dict | None = None, **kwargs
    ) -> httpx.Response:
        """Does an HTTP GET request."""

        response = await self._client.get(url, headers=headers, **kwargs)
        response.raise_for_status()

        return response

    @contextlib.asynccontextmanager
    async def stream(
        self, url: str, headers: dict | None = None, **kwargs
    ) -> AsyncGenerator[httpx.Response]:
        """Does an HTTP GET request and returns a stream."""

        async with self._client.stream(
            "GET", url, headers=headers, **kwargs
        ) as response:
            response.raise_for_status()
            yield response

    async def aclose(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()


@contextlib.asynccontextmanager
async def get_client(**kwargs) -> AsyncGenerator[Client]:
    """Async context manager that yields a Client and closes it afterwards."""
    client = Client(**kwargs)
    try:
        yield client
    finally:
        await client.aclose()
