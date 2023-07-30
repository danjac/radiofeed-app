import contextlib
from collections.abc import Generator

import requests
from django.conf import settings


class HTTPClient:
    """HTTP client wrapper."""

    _DEFAULT_TIMEOUT: int = 10

    def __init__(self, session: requests.Session):
        self.session = session

    def get(
        self,
        url: str,
        params: dict | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
        **kwargs,
    ) -> requests.Response:
        """Do an HTTP GET request."""
        response = self.session.get(url, params=params, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response


@contextlib.contextmanager
def http_client(headers: dict | None = None) -> Generator[HTTPClient, None, None]:
    """Returns HTTPClient instance."""

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": settings.USER_AGENT,
            **(headers or {}),
        }
    )

    with session:
        yield HTTPClient(session)
