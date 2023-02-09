from __future__ import annotations

from radiofeed.settings.base import *  # noqa
from radiofeed.settings.base import (
    ADMIN_SITE_HEADER,
    INSTALLED_APPS,
    MIDDLEWARE,
    configure_templates,
)

DEBUG = True

# INTERNAL_IPS required for debug toolbar

INTERNAL_IPS = ["127.0.0.1"]

INSTALLED_APPS += [
    "debug_toolbar",
    "django_browser_reload",
    "whitenoise.runserver_nostatic",
]

MIDDLEWARE += [
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ADMIN_SITE_HEADER += " [DEVELOPMENT]"

TEMPLATES = configure_templates(debug=True)
