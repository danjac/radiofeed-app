from __future__ import annotations

from split_settings.tools import include

from radiofeed.settings.base import ADMIN_SITE_HEADER, BASE_DIR

include("base.py")
include("mailgun.py")
include("sentry.py")
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
