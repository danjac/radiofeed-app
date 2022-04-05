import socket

from split_settings.tools import include

from jcasts.settings.base import ADMIN_SITE_HEADER, INSTALLED_APPS

include("base.py")

ADMIN_SITE_HEADER += " [LOCAL DEVELOPMENT]"

DEBUG = True

INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS

# internal Docker IP

_, _, INTERNAL_IPS = socket.gethostbyname_ex(socket.gethostname())  # type: ignore
