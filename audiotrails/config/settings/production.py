import sentry_sdk

from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger
from split_settings.tools import include

from audiotrails.config.settings.base import BASE_DIR, INSTALLED_APPS, env

include("base.py")

# AWS/static/media settings

AWS_MEDIA_LOCATION = env("AWS_MEDIA_LOCATION", default="media")
AWS_STATIC_LOCATION = env("AWS_STATIC_LOCATION", default="static")

AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default=None)
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default=None)
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default=None)
AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None)
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="eu-north-1")

AWS_QUERYSTRING_AUTH = False
AWS_IS_GZIPPED = True
AWS_DEFAULT_ACL = "public-read"

AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=1209600, public"}
AWS_STATIC_CLOUDFRONT_DOMAIN = env("AWS_STATIC_CLOUDFRONT_DOMAIN", default=None)

STATIC_URL = "https://" + AWS_STATIC_CLOUDFRONT_DOMAIN + "/" + AWS_STATIC_LOCATION + "/"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
DEFAULT_FILE_STORAGE = "audiotrails.common.storages.MediaStorage"

STATIC_ROOT = BASE_DIR / "staticfiles"

# Mailgun settings

CELERY_EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"

MAILGUN_API_KEY = env("MAILGUN_API_KEY")
MAILGUN_SENDER_DOMAIN = env("MAILGUN_SENDER_DOMAIN")

ANYMAIL = {
    "MAILGUN_API_KEY": MAILGUN_API_KEY,
    "MAILGUN_SENDER_DOMAIN": MAILGUN_SENDER_DOMAIN,
}

SERVER_EMAIL = f"errors@{MAILGUN_SENDER_DOMAIN}"
DEFAULT_FROM_EMAIL = f"support@{MAILGUN_SENDER_DOMAIN}"


# https://github.com/jazzband/sorl-thumbnail#frequently-asked-questions

THUMBNAIL_FORCE_OVERWRITE = True

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
    "interest-cohort": [],
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

ignore_logger("django.security.DisallowedHost")

sentry_sdk.init(
    dsn=env("SENTRY_URL"),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.5,
    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True,
)

# Installed apps

INSTALLED_APPS += ["anymail"]
