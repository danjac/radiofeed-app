from django.conf import settings


def cache_timeout(_) -> dict:
    """Returns the CACHE_TIMEOUT setting."""
    return {"CACHE_TIMEOUT": settings.CACHE_TIMEOUT}
