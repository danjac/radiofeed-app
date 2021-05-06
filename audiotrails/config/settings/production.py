from .base import *  # noqa
from .base import BASE_DIR, MIDDLEWARE
from .mixins.aws import *  # noqa
from .mixins.aws import AWS_CLOUDFRONT_STATIC_DOMAIN, AWS_STATIC_LOCATION
from .mixins.mailgun import *  # noqa
from .mixins.secure import *  # noqa
from .mixins.sentry import *  # noqa

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# https://pypi.org/project/django-permissions-policy/

PERMISSIONS_POLICY = {
    "accelerometer": [],
    "ambient-light-sensor": [],
    "camera": [],
    "document-domain": [],
    "encrypted-media": [],
    "fullscreen": [],
    "geolocation": [],
    "gyroscope": [],
    "interest-cohort": [],
    "magnetometer": [],
    "microphone": [],
    "payment": [],
    "usb": [],
}

# http://whitenoise.evans.io/en/stable/django.html

STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_URL = "/".join([AWS_CLOUDFRONT_STATIC_DOMAIN, AWS_STATIC_LOCATION, ""])

# insert middlewares after security middleware

index = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")

MIDDLEWARE[index:index] = [
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django_permissions_policy.PermissionsPolicyMiddleware",
]
