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
        self._logger = logger.bind(request_headers=headers)

    def get(self, url: str, headers: dict | None = None, **kwargs) -> httpx.Response:
        """Does an HTTP GET request."""
        http_logger = self._logger.bind(url=url, request_headers=headers)
        http_logger.debug("HTTP Request")

        try:
            response = self._client.get(url, **kwargs)
        except httpx.HTTPError as exc:
            http_logger.error("HTTP Error", exception=exc)
            raise

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            http_logger.error(
                "HTTP Status Error",
                status=exc.response.status_code,
                response_headers=dict(exc.response.headers),
            )
            raise

        http_logger.success(
            "HTTP Response OK",
            status=response.status_code,
            response_headers=dict(response.headers),
        )
        return response


@functools.cache
def get_client(**kwargs) -> Client:
    """Returns Client instance"""
    return Client(**kwargs)
