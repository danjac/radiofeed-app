from __future__ import annotations

import sentry_sdk

from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger

from radiofeed.settings.base import *  # noqa
from radiofeed.settings.base import (
    BASE_DIR,
    EMAIL_HOST,
    INSTALLED_APPS,
    MIDDLEWARE,
    config,
    configure_admin_site_header,
    configure_databases,
    configure_templates,
)

MIDDLEWARE += [
    "csp.middleware.CSPMiddleware",
]

DATABASES = configure_databases(conn_max_age=360)

TEMPLATES = configure_templates(debug=False)

ADMIN_SITE_HEADER = configure_admin_site_header("PRODUCTION")

# Static files

# http://whitenoise.evans.io/en/stable/django.html

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

STATIC_ROOT = BASE_DIR / "staticfiles"

# Secure settings

# https://docs.djangoproject.com/en/4.1/topics/security/

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

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

# https://anymail.dev/en/v9.0/esps/mailgun/

if MAILGUN_API_KEY := config("MAILGUN_API_KEY", default=None):
    INSTALLED_APPS += ["anymail"]

    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"

    MAILGUN_API_URL = config("MAILGUN_API_URL", default="https://api.mailgun.net/v3")

    ANYMAIL = {
        "MAILGUN_API_KEY": MAILGUN_API_KEY,
        "MAILGUN_API_URL": MAILGUN_API_URL,
        "MAILGUN_SENDER_DOMAIN": EMAIL_HOST,
    }

# Sentry

# https://docs.sentry.io/platforms/python/guides/django/

if SENTRY_URL := config("SENTRY_URL", default=None):
    ignore_logger("django.security.DisallowedHost")

    sentry_sdk.init(
        dsn=SENTRY_URL,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.5,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
    )
