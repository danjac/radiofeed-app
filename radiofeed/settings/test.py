from split_settings.tools import include

from radiofeed.settings.base import ALLOWED_HOSTS, RQ_QUEUES

include("base.py")

LOGGING = None

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

ALLOWED_HOSTS += [".example.com"]

CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

for queue in RQ_QUEUES.values():
    queue["ASYNC"] = False  # type: ignore
    del queue["USE_REDIS_CACHE"]
