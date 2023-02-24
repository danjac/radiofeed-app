from __future__ import annotations

from split_settings.tools import include

from radiofeed.settings.base import INSTALLED_APPS, MIDDLEWARE

include(
    "base.py",
    "admin.py",
    "cache.py",
    "email.py",
    "logging.py",
    "local.py",
)

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
