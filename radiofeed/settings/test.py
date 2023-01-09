from __future__ import annotations

from split_settings.tools import include

from radiofeed.settings.base import TEMPLATES

include("base.py")

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# enable debug for coverage
TEMPLATES[0]["OPTIONS"]["debug"] = True  # type: ignore

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LOGGING = None

CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}

CACHEOPS_ENABLED = False
