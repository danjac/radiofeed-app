import socket

from split_settings.tools import include

from podtracker.settings.base import (
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

# internal Docker IP

_, _, INTERNAL_IPS = socket.gethostbyname_ex(socket.gethostname())  # type: ignore
