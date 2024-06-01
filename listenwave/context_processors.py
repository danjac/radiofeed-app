from django.conf import settings


def cache_timeout(_) -> dict:
    """Returns the CACHE_TIMEOUT setting."""
    return {"cache_timeout": settings.CACHE_TIMEOUT}
