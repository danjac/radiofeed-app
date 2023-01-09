from __future__ import annotations

import sentry_sdk

from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger
from split_settings.tools import include

from radiofeed.settings.base import (
    ADMIN_SITE_HEADER,
    BASE_DIR,
    EMAIL_HOST,
    INSTALLED_APPS,
    env,
)

include("base.py")
include("mailgun.py")
include("templates.py")

ADMIN_SITE_HEADER += " [PRODUCTION]"

# Sessions and cookies

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Static files
#
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Secure settings

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 15768001  # 6 months
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True

# Permissions Policy

# https://pypi.org/project/django-permissions-policy/

PERMISSIONS_POLICY: dict[str, list] = {
    "accelerometer": [],
    "ambient-light-sensor": [],
    "camera": [],
    "document-domain": [],
    "encrypted-media": [],
    "fullscreen": [],
    "geolocation": [],
    "gyroscope": [],
    "magnetometer": [],
    "microphone": [],
    "payment": [],
    "usb": [],
}

# Mailgun

if MAILGUN_API_KEY := env("MAILGUN_API_KEY", default=None):

    INSTALLED_APPS += ["anymail"]

    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"

    MAILGUN_API_URL = env("MAILGUN_API_URL", default="https://api.mailgun.net/v3")

    ANYMAIL = {
        "MAILGUN_API_KEY": MAILGUN_API_KEY,
        "MAILGUN_API_URL": MAILGUN_API_URL,
        "MAILGUN_SENDER_DOMAIN": EMAIL_HOST,
    }

# Sentry

if SENTRY_URL := env("SENTRY_URL", default=None):

    ignore_logger("django.security.DisallowedHost")

    sentry_sdk.init(
        dsn=SENTRY_URL,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.5,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
    )
