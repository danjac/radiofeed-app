from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Warning


def check_secure_admin_url(
    app_configs: list[AppConfig] | None, **kwargs
) -> list[Warning]:
    """Checks ADMIN_URL is not /admin/ in production."""
    if settings.ADMIN_URL == "admin/":
        return [
            Warning(
                "ADMIN_URL should not be admin/",
                hint="Change ADMIN_URL setting in environment to an unguessable URL",
                id="radiofeed.W001",
            )
        ]

    return []
