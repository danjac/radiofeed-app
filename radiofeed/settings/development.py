from __future__ import annotations

from radiofeed.settings.base import INSTALLED_APPS, MIDDLEWARE
from radiofeed.settings.local import *  # noqa

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
