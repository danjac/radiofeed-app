from __future__ import annotations

import pathlib

from email.utils import getaddresses
from typing import Literal

import dj_database_url
import sentry_sdk

from decouple import AutoConfig, Csv
from django.urls import reverse_lazy
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger

Environment = Literal["development", "production", "testing"]

BASE_DIR = pathlib.Path(__file__).resolve(strict=True).parents[2]

config = AutoConfig(search_path=BASE_DIR)

DEBUG: bool = config("DEBUG", default=False, cast=bool)

SECRET_KEY = config(
    "SECRET_KEY",
    default="django-insecure-+-pzc(vc+*=sjj6gx84da3y-2y@h_&f=)@s&fvwwpz_+8(ced^",
)

# Installed apps

INSTALLED_APPS: list[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.postgres",
    "django.contrib.sessions",
    "django.contrib.sitemaps",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "django.forms",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "django_extensions",
    "django_htmx",
    "django_object_actions",
    "heroicons",
    "radiofeed.episodes",
    "radiofeed.feedparser",
    "radiofeed.podcasts",
    "radiofeed.users",
]


# Middleware

MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django_permissions_policy.PermissionsPolicyMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "radiofeed.middleware.CacheControlMiddleware",
    "radiofeed.middleware.OrderingMiddleware",
    "radiofeed.middleware.PaginationMiddleware",
    "radiofeed.middleware.SearchMiddleware",
    "radiofeed.episodes.middleware.PlayerMiddleware",
]


# Databases

DATABASE_URL = config(
    "DATABASE_URL",
    default="postgresql://postgres:password@127.0.0.1:5432/postgres",
)

CONN_MAX_AGE = config("CONN_MAX_AGE", cast=int, default=0)

DATABASES = {
    "default": {
        **dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=CONN_MAX_AGE,
            conn_health_checks=CONN_MAX_AGE > 0,
        ),
        "ATOMIC_REQUESTS": True,
    },
}

# Caches

REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/0")

CACHES: dict = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Mimicing memcache behavior.
            # https://github.com/jazzband/django-redis#memcached-exceptions-behavior
            "IGNORE_EXCEPTIONS": True,
            "PARSER_CLASS": "redis.connection.HiredisParser",
        },
    }
}

# Templates

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": config("TEMPLATE_DEBUG", default=False, cast=bool),
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
            "builtins": [
                "radiofeed.template",
            ],
        },
    }
]


# prevent deprecation warnings
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Server settings

ROOT_URLCONF = "radiofeed.config.urls"

ALLOWED_HOSTS: list[str] = config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv()
)

# User-Agent header for API calls from this site
USER_AGENT = config("USER_AGENT", "Radiofeed/0.0.0")

SITE_ID = 1

# Session and cookies

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Secure settings

# https://docs.djangoproject.com/en/4.1/topics/security/

if config("USE_SECURE_SETTINGS", default=True, cast=bool):
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


# Email configuration

EMAIL_HOST = config("EMAIL_HOST", default="127.0.0.1")
EMAIL_PORT = config("EMAIL_PORT", default=1025, cast=int)

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
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

ADMINS = getaddresses(config("ADMINS", default="", cast=Csv()))

SERVER_EMAIL = config("SERVER_EMAIL", default=f"errors@{EMAIL_HOST}")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default=f"no-reply@{EMAIL_HOST}")

# email shown in about page etc
CONTACT_EMAIL = config("CONTACT_EMAIL", default=f"support@{EMAIL_HOST}")

# admin settings

ADMIN_URL = config("ADMIN_URL", default="admin/")

ADMIN_SITE_HEADER = config("ADMIN_SITE_HEADER", default="Radiofeed Admin")

# Authentication

AUTH_USER_MODEL = "users.User"

# https://django-allauth.readthedocs.io/en/latest/configuration.html

ACCOUNT_EMAIL_VERIFICATION = "mandatory"

# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_REDIRECT_URL = reverse_lazy("podcasts:index")

LOGIN_URL = "account_login"

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
    }
}

# Internationalization/Localization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = "en"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files

STATIC_URL = config("STATIC_URL", default="/static/")
STATICFILES_DIRS = [BASE_DIR / "static"]

if config("USE_COLLECTSTATIC", default=True, cast=bool):
    STORAGES = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

    STATIC_ROOT = BASE_DIR / "staticfiles"

else:
    INSTALLED_APPS += ["whitenoise.runserver_nostatic"]

# Templates

# https://docs.djangoproject.com/en/1.11/ref/forms/renderers/

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# Logging

LOGGING: dict | None = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "null": {"level": "DEBUG", "class": "logging.NullHandler"},
    },
    "loggers": {
        "root": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security.DisallowedHost": {
            "handlers": ["null"],
            "propagate": False,
        },
        "django.request": {
            "level": "CRITICAL",
            "propagate": False,
        },
    },
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

if config("USE_DEBUG_TOOLBAR", default=False, cast=bool):
    INSTALLED_APPS += ["debug_toolbar"]

    MIDDLEWARE += [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    ]
    # INTERNAL_IPS required for debug toolbar
    INTERNAL_IPS = ["127.0.0.1"]

if config("USE_BROWSER_RELOAD", default=False, cast=bool):
    INSTALLED_APPS += ["django_browser_reload"]

    MIDDLEWARE += [
        "django_browser_reload.middleware.BrowserReloadMiddleware",
    ]
