from __future__ import annotations

from split_settings.tools import include

include("base.py")
include("debug.py")

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LOGGING = None

CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}

CACHEOPS_ENABLED = False
