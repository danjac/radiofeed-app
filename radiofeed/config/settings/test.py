from split_settings.tools import include

from radiofeed.config.settings.base import ALLOWED_HOSTS, HUEY

include("base.py")

LOGGING = None

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

ALLOWED_HOSTS += [".example.com"]

CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}

HUEY["immediate"] = True
