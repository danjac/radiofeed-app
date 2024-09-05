from django.conf import settings
from django.http import HttpHeaders, HttpRequest


def cache_timeout(request: HttpRequest) -> dict:
    """Returns the DEFAULT_CACHE_TIMEOUT setting."""

    return {"CACHE_TIMEOUT": settings.CACHE_TIMEOUT}


def csrf_header(request: HttpRequest) -> dict:
    """Returns the CSRF header, based on CSRF_HEADER_NAME setting."""

    return {"CSRF_HEADER": HttpHeaders.parse_header_name(settings.CSRF_HEADER_NAME)}
