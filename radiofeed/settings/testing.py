from __future__ import annotations

from radiofeed.settings.base import *  # noqa
from radiofeed.settings.base import REDIS_URL, configure_databases, configure_templates

DATABASES = configure_databases(conn_max_age=0)

TEMPLATES = configure_templates(debug=True)

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LOGGING = None

CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}

# https://github.com/rq/django-rq#synchronous-mode

RQ_QUEUES = {"default": {"URL": REDIS_URL}}

for queueConfig in RQ_QUEUES.values():
    queueConfig["ASYNC"] = False  # type: ignore
