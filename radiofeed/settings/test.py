from __future__ import annotations

from split_settings.tools import include

from radiofeed.settings.base import ALLOWED_HOSTS, HUEY, TEMPLATES

include("base.py")

LOGGING = None

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

ALLOWED_HOSTS += [".example.com"]

CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# django-coverage-plugin
TEMPLATES[0]["OPTIONS"]["debug"] = True  # type: ignore

HUEY["immediate"] = True  # type: ignore
