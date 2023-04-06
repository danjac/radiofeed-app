from __future__ import annotations

import pathlib

from email.utils import getaddresses

import environ
import sentry_sdk

from django.urls import reverse_lazy
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger

# default flags
env = environ.Env(
    DEBUG=(bool, False),
    TEMPLATE_DEBUG=(bool, False),
    USE_BROWSER_RELOAD=(bool, False),
    USE_DEBUG_TOOLBAR=(bool, False),
    USE_COLLECTSTATIC=(bool, True),
    USE_SECURE_SETTINGS=(bool, True),
)

BASE_DIR = pathlib.Path(__file__).resolve(strict=True).parents[2]

environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env("DEBUG")
TEMPLATE_DEBUG = env("TEMPLATE_DEBUG")

USE_BROWSER_RELOAD = env("USE_BROWSER_RELOAD")
USE_DEBUG_TOOLBAR = env("USE_DEBUG_TOOLBAR")
USE_COLLECTSTATIC = env("USE_COLLECTSTATIC")
USE_SECURE_SETTINGS = env("USE_SECURE_SETTINGS")

SECRET_KEY = env.str(
    "SECRET_KEY",
    default="django-insecure-+-pzc(vc+*=sjj6gx84da3y-2y@h_&f=)@s&fvwwpz_+8(ced^",
)

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

CONN_MAX_AGE = env.int("CONN_MAX_AGE", default=0)

DATABASES = {
    "default": {
        **env.db(default="postgresql://postgres:password@127.0.0.1:5432/postgres"),
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": CONN_MAX_AGE,
        "CONN_HEALTH_CHECKS": CONN_MAX_AGE > 0,
    }
}

# Caches

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env.str("REDIS_URL", default="redis://127.0.0.1:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
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
            "debug": TEMPLATE_DEBUG,
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

ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# User-Agent header for API calls from this site
USER_AGENT = env.str("USER_AGENT", default="Radiofeed/0.0.0")

SITE_ID = 1

# Session and cookies

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Email configuration

EMAIL_HOST = env.str("EMAIL_HOST", default="127.0.0.1")
EMAIL_PORT = env.int("EMAIL_PORT", default=1025)

# Mailgun
# https://anymail.dev/en/v9.0/esps/mailgun/

if MAILGUN_API_KEY := env.str("MAILGUN_API_KEY", default=None):
    INSTALLED_APPS += ["anymail"]

    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"

    MAILGUN_API_URL = env.str("MAILGUN_API_URL", default="https://api.mailgun.net/v3")

    ANYMAIL = {
        "MAILGUN_API_KEY": MAILGUN_API_KEY,
        "MAILGUN_API_URL": MAILGUN_API_URL,
        "MAILGUN_SENDER_DOMAIN": EMAIL_HOST,
    }
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

ADMINS = getaddresses(env.list("ADMINS", default=[]))

SERVER_EMAIL = env.str("SERVER_EMAIL", default=f"errors@{EMAIL_HOST}")
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default=f"no-reply@{EMAIL_HOST}")

# email shown in about page etc
CONTACT_EMAIL = env.str("CONTACT_EMAIL", default=f"support@{EMAIL_HOST}")

# admin settings

ADMIN_URL = env.str("ADMIN_URL", default="admin/")

ADMIN_SITE_HEADER = env.str("ADMIN_SITE_HEADER", default="Radiofeed Admin")

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

STATIC_URL = env.str("STATIC_URL", default="/static/")
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

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

if SENTRY_URL := env.str("SENTRY_URL", default=None):
    ignore_logger("django.security.DisallowedHost")

    sentry_sdk.init(
        dsn=SENTRY_URL,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.5,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
    )

# Secure settings
# https://docs.djangoproject.com/en/4.1/topics/security/

if USE_SECURE_SETTINGS:
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


# Debug toolbar
# https://django-debug-toolbar.readthedocs.io/en/latest/

if USE_DEBUG_TOOLBAR:
    INSTALLED_APPS += ["debug_toolbar"]

    MIDDLEWARE += [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    ]
    # INTERNAL_IPS required for debug toolbar
    INTERNAL_IPS = ["127.0.0.1"]

# Browser reload
# https://github.com/adamchainz/django-browser-reload

if USE_BROWSER_RELOAD:
    INSTALLED_APPS += ["django_browser_reload"]

    MIDDLEWARE += [
        "django_browser_reload.middleware.BrowserReloadMiddleware",
    ]

# Whitenoise
# https://whitenoise.readthedocs.io/en/latest/django.html

if USE_COLLECTSTATIC:
    STORAGES = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }


else:
    INSTALLED_APPS += ["whitenoise.runserver_nostatic"]
