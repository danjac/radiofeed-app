from __future__ import annotations

from split_settings.tools import include

from radiofeed.config.settings.base import ALLOWED_HOSTS, TEMPLATES

include("base.py")

LOGGING = None

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

ALLOWED_HOSTS += [".example.com"]

CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
CACHEOPS_ENABLED = False

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# django-coverage-plugin
TEMPLATES[0]["OPTIONS"]["debug"] = True  # type: ignore

DEBUG_ERROR_PAGES = True
