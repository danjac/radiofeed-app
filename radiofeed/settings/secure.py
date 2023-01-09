# Sessions and cookies

from __future__ import annotations

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

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
