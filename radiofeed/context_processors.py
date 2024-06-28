from django.conf import settings


def cache_timeout(_) -> dict:
    """Returns the CACHE_TIMEOUT setting."""
    return {"CACHE_TIMEOUT": settings.CACHE_TIMEOUT}


def page_size(_) -> dict:
    """Returns the PAGE_SIZE setting."""
    return {"PAGE_SIZE": settings.PAGE_SIZE}


def theme_color(_) -> dict:
    """Returns the THEME_COLOR setting for PWA."""
    return {"THEME_COLOR": settings.THEME_COLOR}
