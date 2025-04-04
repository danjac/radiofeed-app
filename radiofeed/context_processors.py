from django.conf import settings


def cache_timeout(_) -> dict[str, str]:
    """Returns default cache timeout"""
    return {
        "cache_timeout": settings.DEFAULT_CACHE_TIMEOUT,
    }
