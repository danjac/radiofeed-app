# Local
from .base import *  # noqa
from .base import INSTALLED_APPS, MIDDLEWARE, TEMPLATES

DEBUG = True
THUMBNAIL_DEBUG = True
TEMPLATES[0]["OPTIONS"]["debug"] = True

INSTALLED_APPS += ["silk"]

MIDDLEWARE = ["silk.middleware.SilkyMiddleware"] + MIDDLEWARE
