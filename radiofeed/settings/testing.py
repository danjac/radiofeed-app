from __future__ import annotations

from radiofeed.settings.base import *  # noqa
from radiofeed.settings.base import configure_databases, configure_templates

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LOGGING = None

CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}

DATABASES = configure_databases(conn_max_age=0)

TEMPLATES = configure_templates(debug=True)
