import functools

import requests
from django.conf import settings


class HTTPClient:
    """HTTP client wrapper."""

    _DEFAULT_TIMEOUT: int = 10

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": settings.USER_AGENT})

    def get(
        self,
        url: str,
        params: dict | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
        **kwargs,
    ) -> requests.Response:
        """Do an HTTP GET request."""
        response = self._session.get(url, params=params, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response


@functools.cache
def http_client() -> HTTPClient:
    """Returns HTTPClient singleton instance."""
    return HTTPClient()
