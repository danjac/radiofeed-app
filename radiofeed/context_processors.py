import functools

from django.conf import settings


def cache_timeout(_) -> dict[str, str]:
    """Returns default cache timeout"""
    return {
        "cache_timeout": settings.DEFAULT_CACHE_TIMEOUT,
    }


def csrf_header(_) -> dict[str, str]:
    """
    Based on the Django setting CSRF_HEADER_NAME, the CSRF header name is returned
    """
    return {
        "csrf_header": _csrf_header(),
    }


@functools.cache
def _csrf_header() -> str:
    return settings.CSRF_HEADER_NAME[5:].replace("_", "-").lower()
