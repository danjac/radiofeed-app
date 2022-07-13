from __future__ import annotations

from debug_toolbar.settings import PANELS_DEFAULTS
from split_settings.tools import include

from radiofeed.settings.base import (
    ADMIN_SITE_HEADER,
    INSTALLED_APPS,
    LOGGING,
    MIDDLEWARE,
)

include("base.py")

DEBUG = True

ADMIN_SITE_HEADER += " [LOCAL]"

INSTALLED_APPS = [
    "whitenoise.runserver_nostatic",
    "debug_toolbar",
    "silk",
] + INSTALLED_APPS

MIDDLEWARE += [
    "silk.middleware.SilkyMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

INTERNAL_IPS = ["127.0.0.1"]

# log DB queries

LOGGING["loggers"]["django.db.backends"] = {  # type: ignore
    "level": "DEBUG",
    "handlers": ["console"],
    "propagate": False,
}

DEBUG_TOOLBAR_PANELS = PANELS_DEFAULTS + [
    "cachalot.panels.CachalotPanel",
]
