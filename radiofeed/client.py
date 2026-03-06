import contextlib
import dataclasses
import json
from typing import TYPE_CHECKING, Any

import aiohttp
from django.conf import settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping


@dataclasses.dataclass(kw_only=True)
class BaseClientResponse:
    """Base HTTP response wrapping an aiohttp response."""

    response: aiohttp.ClientResponse

    @property
    def status(self) -> int:
        """HTTP status code."""
        return self.response.status

    @property
    def headers(self) -> Mapping[str, str]:
        """HTTP response headers."""
        return self.response.headers

    @property
    def url(self) -> str:
        """Final URL after redirects."""
        return str(self.response.url)


@dataclasses.dataclass(kw_only=True)
class ClientResponse(BaseClientResponse):
    """HTTP response with pre-read body."""

    content: bytes

    async def json(self, **kwargs: Any) -> Any:
        """Parses the response body as JSON."""
        return json.loads(self.content)


@dataclasses.dataclass(kw_only=True)
class StreamingClientResponse(BaseClientResponse):
    """HTTP response that streams the body without buffering."""

    reader: aiohttp.StreamReader


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
        """Does an HTTP GET request and returns a pre-read response."""

        async with self._get(url, headers=headers, **kwargs) as response:
            return ClientResponse(response=response, content=await response.read())

    @contextlib.asynccontextmanager
    async def stream(
        self, url: str, headers: dict | None = None, **kwargs
    ) -> AsyncGenerator[StreamingClientResponse]:
        """Does an HTTP GET request and yields a streaming response."""

        async with self._get(url, headers=headers, **kwargs) as response:
            yield StreamingClientResponse(response=response, reader=response.content)

    @contextlib.asynccontextmanager
    async def _get(
        self, url: str, headers: dict | None = None, **kwargs
    ) -> AsyncGenerator[aiohttp.ClientResponse]:
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
