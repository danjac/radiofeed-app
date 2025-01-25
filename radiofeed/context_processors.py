from django.conf import settings


def csrf_header(_) -> dict[str, str]:
    """
    Based on the Django setting CSRF_HEADER_NAME, the CSRF header name is returned
    """
    return {
        "csrf_header": settings.CSRF_HEADER_NAME[5:].replace("_", "-").lower(),
    }
