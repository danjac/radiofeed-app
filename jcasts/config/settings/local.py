import socket

from split_settings.tools import include

from jcasts.config.settings.base import INSTALLED_APPS, TEMPLATES

include("base.py")

ADMIN_SITE_HEADER = "jCasts Admin [LOCAL DEVELOPMENT]"

DEBUG = True
THUMBNAIL_DEBUG = True
TEMPLATES[0]["OPTIONS"]["debug"] = True

INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS

# internal Docker IP

_, _, INTERNAL_IPS = socket.gethostbyname_ex(socket.gethostname())  # type: ignore
