import dataclasses
import functools

import httpx
from loguru import logger


@dataclasses.dataclass
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
        self._client = httpx.Client(
            headers=headers,
            follow_redirects=follow_redirects,
            timeout=timeout,
            **kwargs,
        )

    def get(self, url: str, **kwargs) -> httpx.Response:
        """Does an HTTP GET request."""
        http_logger = logger.bind(url=url)
        http_logger.debug("Request")
        response = self._client.get(url, **kwargs)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            http_logger.error("Response Error", status=exc.response.status_code)
            raise
        http_logger.success("Response OK", status=response.status_code)
        return response


@functools.cache
def get_client(**kwargs) -> Client:
    """Returns Client instance"""
    return Client(**kwargs)
