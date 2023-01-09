from __future__ import annotations

from split_settings.tools import include

from radiofeed.settings.base import (
    ADMIN_SITE_HEADER,
    INSTALLED_APPS,
    MIDDLEWARE,
    TEMPLATES,
)

include("base.py")

DEBUG = True

INSTALLED_APPS += [
    "debug_toolbar",
    "django_browser_reload",
    "whitenoise.runserver_nostatic",
]

MIDDLEWARE += [
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

TEMPLATES[0]["OPTIONS"]["debug"] = True  # type: ignore

ADMIN_SITE_HEADER += " [DEVELOPMENT]"
