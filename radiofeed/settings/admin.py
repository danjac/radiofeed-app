from __future__ import annotations

from email.utils import getaddresses

from radiofeed.settings.base import Csv, config

ADMINS = getaddresses(config("ADMINS", default="", cast=Csv()))

ADMIN_URL = config("ADMIN_URL", default="admin/")

ADMIN_SITE_HEADER = config("ADMIN_SITE_HEADER", default="Radiofeed Admin")


def admin_site_header(environment: str) -> str:
    """Add admin header with environment suffix."""
    return f"{ADMIN_SITE_HEADER} [{environment}]"
