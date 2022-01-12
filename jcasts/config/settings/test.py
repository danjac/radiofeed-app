from split_settings.tools import include

from jcasts.config.settings.base import ALLOWED_HOSTS

include("base.py")

LOGGING = None

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

ALLOWED_HOSTS += [".example.com"]

CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}

RQ_QUEUES = {
    "default": {
        "ASYNC": False,
    },
    "feeds": {
        "ASYNC": False,
    },
    "mail": {
        "ASYNC": False,
    },
}
