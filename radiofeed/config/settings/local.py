from __future__ import annotations

from split_settings.tools import include

from radiofeed.config.settings.base import ADMIN_SITE_HEADER, INSTALLED_APPS, MIDDLEWARE

include("base.py")

DEBUG = True


ADMIN_SITE_HEADER += " [LOCAL]"

INSTALLED_APPS = [
    "whitenoise.runserver_nostatic",
    "debug_toolbar",
    "silk",
    "django_browser_reload",
    "django_watchfiles",
] + INSTALLED_APPS

# gzip middleware incompatible with browser reload
MIDDLEWARE.remove("django.middleware.gzip.GZipMiddleware")

MIDDLEWARE += [
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "silk.middleware.SilkyMiddleware",
]


INTERNAL_IPS = ["127.0.0.1"]

DEBUG_ERROR_PAGES = True
