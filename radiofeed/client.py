import contextlib
import dataclasses
import json as json_module
from typing import TYPE_CHECKING, Any

import aiohttp
from django.conf import settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from collections.abc import Mapping


@dataclasses.dataclass(kw_only=True)
class ClientResponse:
    """Lightweight HTTP response container with pre-read body."""

    status: int
    headers: Mapping[str, str]
    url: str
    content: bytes

    async def read(self) -> bytes:
        """Returns the response body."""
        return self.content

    async def json(self, **kwargs: Any) -> Any:
        """Parses the response body as JSON."""
        return json_module.loads(self.content)


class Client:
    """Handles HTTP GET requests."""

    def __init__(
        self,
        headers: dict | None = None,
        *,
        timeout: int = 5,
        **kwargs,
    ) -> None:
        headers = {
            "User-Agent": settings.USER_AGENT,
        } | (headers or {})

        self._session = aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout),
            **kwargs,
        )

    async def get(
        self, url: str, headers: dict | None = None, **kwargs
    ) -> ClientResponse:
        """Does an HTTP GET request."""

        async with self._session.get(url, headers=headers, **kwargs) as response:
            response.raise_for_status()
            return ClientResponse(
                status=response.status,
                headers=response.headers,
                url=str(response.url),
                content=await response.read(),
            )

    @contextlib.asynccontextmanager
    async def stream(
        self, url: str, headers: dict | None = None, **kwargs
    ) -> AsyncGenerator[aiohttp.ClientResponse]:
        """Does an HTTP GET request and returns a stream."""

        async with self._session.get(url, headers=headers, **kwargs) as response:
            response.raise_for_status()
            yield response

    async def aclose(self) -> None:
        """Close the underlying aiohttp session."""
        await self._session.close()


@contextlib.asynccontextmanager
async def get_client(**kwargs) -> AsyncGenerator[Client]:
    """Async context manager that yields a Client and closes it afterwards."""
    client = Client(**kwargs)
    try:
        yield client
    finally:
        await client.aclose()
