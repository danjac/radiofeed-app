import functools

from django.conf import settings
from django.http import HttpHeaders, HttpRequest


def cache_timeout(request: HttpRequest) -> dict[str, int]:
    """Returns the DEFAULT_CACHE_TIMEOUT setting."""

    return {"CACHE_TIMEOUT": settings.DEFAULT_CACHE_TIMEOUT}


def csrf_header(request: HttpRequest) -> dict[str, str | None]:
    """Returns the CSRF header, based on CSRF_HEADER_NAME setting."""

    return {"CSRF_HEADER": _csrf_header_name()}


@functools.cache
def _csrf_header_name() -> str | None:
    return HttpHeaders.parse_header_name(settings.CSRF_HEADER_NAME)
