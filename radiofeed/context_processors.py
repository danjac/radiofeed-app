import functools

from django.conf import settings
from django.http import HttpHeaders


def cache_timeout(_) -> dict[str, str]:
    """Returns default cache timeout"""
    return {"cache_timeout": settings.DEFAULT_CACHE_TIMEOUT}


def csrf_header(_) -> dict[str, str | None]:
    """Returns CSRF header name"""
    return {"csrf_header": _csrf_header_name()}


@functools.cache
def _csrf_header_name() -> str | None:
    return HttpHeaders.parse_header_name(settings.CSRF_HEADER_NAME)
