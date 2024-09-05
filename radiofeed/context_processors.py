from django.conf import settings
from django.http import HttpRequest


def cache_timeout(request: HttpRequest) -> dict:
    """Returns the DEFAULT_CACHE_TIMEOUT setting."""

    return {"CACHE_TIMEOUT": settings.CACHE_TIMEOUT}


def csrf_header(request: HttpRequest) -> dict:
    """Returns the CSRF header, based on CSRF_HEADER_NAME setting."""

    header = settings.CSRF_HEADER_NAME.removeprefix("HTTP_").replace("_", "-")

    return {"CSRF_HEADER": header}
