from __future__ import annotations

from radiofeed.settings.base import *  # noqa

DOMAIN_NAME = "example.com"

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# enable debug for coverage
TEMPLATES[0]["OPTIONS"]["debug"] = True  # type: ignore # noqa

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LOGGING = None

CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}

CACHEOPS_ENABLED = False
