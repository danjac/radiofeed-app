from __future__ import annotations

from radiofeed.settings.base import *  # noqa
from radiofeed.settings.base import ADMIN_SITE_HEADER, BASE_DIR

ADMIN_SITE_HEADER += " [PRODUCTION]"

# Set HTTPS for absolute uris in allauth and our own absolute links

ACCOUNT_DEFAULT_HTTP_PROTOCOL = HTTP_PROTOCOL = "https"

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
