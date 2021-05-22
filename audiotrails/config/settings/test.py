# Local
from audiotrails.config.settings.base import *  # noqa
from audiotrails.config.settings.base import ALLOWED_HOSTS

LOGGING = None

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

ALLOWED_HOSTS += [".example.com"]

CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
