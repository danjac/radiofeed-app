from __future__ import annotations

from radiofeed.settings.base import *  # noqa
from radiofeed.settings.base import configure_templates

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LOGGING = None

CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}

CACHEOPS_ENABLED = False

TEMPLATES = configure_templates(debug=True)
