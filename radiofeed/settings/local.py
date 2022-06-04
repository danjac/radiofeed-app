from split_settings.tools import include

from radiofeed.settings.base import (
    ADMIN_SITE_HEADER,
    INSTALLED_APPS,
    MIDDLEWARE,
    TEMPLATES,
)

include("base.py")

ADMIN_SITE_HEADER += " [LOCAL]"

DEBUG = True

TEMPLATES[0]["OPTIONS"]["debug"] = True

INSTALLED_APPS = ["whitenoise.runserver_nostatic", "debug_toolbar"] + INSTALLED_APPS

MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]

INTERNAL_IPS = ["127.0.0.1"]
