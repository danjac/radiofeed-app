import sentry_sdk

from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger
from split_settings.tools import include

from radiofeed.settings.base import ADMIN_SITE_HEADER, BASE_DIR, INSTALLED_APPS, env

include("base.py")

ADMIN_SITE_HEADER += " [PRODUCTION]"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

STATIC_ROOT = BASE_DIR / "staticfiles"

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


# Secure settings for production environment

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 15768001  # 6 months
SECURE_SSL_REDIRECT = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

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


# Mailgun

MAILGUN_API_KEY = env("MAILGUN_API_KEY", default=None)
MAILGUN_SENDER_DOMAIN = env("MAILGUN_SENDER_DOMAIN", default=None)

if MAILGUN_API_KEY and MAILGUN_SENDER_DOMAIN:

    INSTALLED_APPS += ["anymail"]

    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"

    MAILGUN_API_URL = env("MAILGUN_API_URL", default="https://api.mailgun.net/v3")

    ANYMAIL = {
        "MAILGUN_API_KEY": MAILGUN_API_KEY,
        "MAILGUN_API_URL": MAILGUN_API_URL,
        "MAILGUN_SENDER_DOMAIN": MAILGUN_SENDER_DOMAIN,
    }

    SERVER_EMAIL = f"errors@{MAILGUN_SENDER_DOMAIN}"
    DEFAULT_FROM_EMAIL = f"support@{MAILGUN_SENDER_DOMAIN}"
