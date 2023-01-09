from __future__ import annotations

import pathlib

from email.utils import getaddresses
from typing import Literal

import environ

from django.contrib.messages import constants as messages
from django.urls import reverse_lazy

Environments = Literal["development", "production", "test"]

BASE_DIR = pathlib.Path(__file__).resolve(strict=True).parents[1]

env = environ.Env()

environ.Env.read_env(BASE_DIR / ".env")

ENVIRONMENT: Environments = env("ENVIRONMENT", default="development")

DEVELOPMENT = ENVIRONMENT == "development"
PRODUCTION = ENVIRONMENT == "production"
TESTING = ENVIRONMENT == "test"

DEBUG = DEVELOPMENT
TEMPLATE_DEBUG = DEVELOPMENT or TESTING

SECRET_KEY = env("SECRET_KEY")

DATABASES = {
    "default": {
        **env.db(),
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": 360,
    },
}

REDIS_URL = env("REDIS_URL")

# prevent deprecation warnings
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Server settings

if TESTING:
    DOMAIN_NAME = "example.com"
else:
    DOMAIN_NAME = env("DOMAIN_NAME", default="localhost")

HTTP_PROTOCOL = "https" if PRODUCTION else "http"

BASE_URL = f"{HTTP_PROTOCOL}://{DOMAIN_NAME}"

ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS", default=[DOMAIN_NAME])

SITE_ID = 1

# Session and cookies

SESSION_COOKIE_DOMAIN = env("SESSION_COOKIE_DOMAIN", default=None)
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

CSRF_COOKIE_DOMAIN = env("CSRF_COOKIE_DOMAIN", default=None)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

if PRODUCTION:

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Email configuration

EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)

# Mailgun

if MAILGUN_API_KEY := env("MAILGUN_API_KEY", default=None):

    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"

    MAILGUN_API_URL = env("MAILGUN_API_URL", default="https://api.mailgun.net/v3")

    ANYMAIL = {
        "MAILGUN_API_KEY": MAILGUN_API_KEY,
        "MAILGUN_API_URL": MAILGUN_API_URL,
        "MAILGUN_SENDER_DOMAIN": EMAIL_HOST,
    }

elif TESTING:
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

ADMINS = getaddresses(env.list("ADMINS", default=[]))

SERVER_EMAIL = f"errors@{EMAIL_HOST}"
DEFAULT_FROM_EMAIL = f"no-reply@{EMAIL_HOST}"

# email shown in about page etc
CONTACT_EMAIL = env("CONTACT_EMAIL", default=f"admin@{EMAIL_HOST}")

ROOT_URLCONF = "radiofeed.urls"

# Installed apps

DJANGO_APPS: list[str] = [
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
]

THIRD_PARTY_APPS: list[str] = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "cacheops",
    "django_extensions",
    "django_htmx",
    "django_object_actions",
    "fast_update",
    "widget_tweaks",
]

if DEVELOPMENT:
    THIRD_PARTY_APPS += [
        "debug_toolbar",
        "django_browser_reload",
        "whitenoise.runserver_nostatic",
    ]

if PRODUCTION:
    THIRD_PARTY_APPS += ["anymail"]

PROJECT_APPS: list[str] = [
    "radiofeed.episodes",
    "radiofeed.feedparser",
    "radiofeed.podcasts",
    "radiofeed.users",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS

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
    "radiofeed.common.middleware.cache_control_middleware",
    "radiofeed.common.middleware.search_middleware",
    "radiofeed.common.middleware.sorter_middleware",
    "radiofeed.episodes.middleware.player_middleware",
]

if DEVELOPMENT:
    MIDDLEWARE += [
        "django_browser_reload.middleware.BrowserReloadMiddleware",
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    ]


# admin settings

ADMIN_URL = env("ADMIN_URL", default="admin/")

ADMIN_SITE_HEADER = (
    env("ADMIN_SITE_HEADER", default="Radiofeed Admin") + f" [{ENVIRONMENT.upper()}]"
)

# Authentication

AUTH_USER_MODEL = "users.User"

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

if TESTING:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

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

STATIC_URL = env("STATIC_URL", default="/static/")
STATICFILES_DIRS = [BASE_DIR / "static"]

if PRODUCTION:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
    STATIC_ROOT = BASE_DIR / "staticfiles"

# Templates

# https://docs.djangoproject.com/en/1.11/ref/forms/renderers/

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

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
                "radiofeed.common.template",
            ],
        },
    }
]

# Logging

if TESTING:
    LOGGING = None
else:
    LOGGING = {
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

if SENTRY_URL := env("SENTRY_URL", default=None):
    import sentry_sdk

    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import ignore_logger

    ignore_logger("django.security.DisallowedHost")

    sentry_sdk.init(
        dsn=SENTRY_URL,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.5,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
    )

# Messages

# https://docs.djangoproject.com/en/4.1/ref/contrib/messages/

MESSAGE_TAGS = {
    messages.DEBUG: "bg-gray-600",
    messages.ERROR: "bg-red-600",
    messages.INFO: "bg-blue-600",
    messages.SUCCESS: "bg-green-600",
    messages.WARNING: "bg-violet-600",
}

# Caches

if TESTING:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
else:
    CACHES = {
        "default": {
            **env.cache("REDIS_URL"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                # Mimicing memcache behavior.
                # https://github.com/jazzband/django-redis#memcached-exceptions-behavior
                "IGNORE_EXCEPTIONS": True,
                "PARSER_CLASS": "redis.connection.HiredisParser",
            },
        },
    }

# Cacheops

# https://github.com/Suor/django-cacheops

if TESTING:
    CACHEOPS_ENABLED = False
else:
    CACHEOPS_REDIS = REDIS_URL
    CACHEOPS_DEFAULTS = {"timeout": 300}
    CACHEOPS_DEGRADE_ON_FAILURE = True

    CACHEOPS = {
        "podcasts.*": {"ops": "all"},
        "episodes.*": {"ops": "all"},
        "users.*": {"ops": "all"},
    }

# Secure settings

if PRODUCTION:

    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_HSTS_SECONDS = 15768001  # 6 months
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True

# Permissions Policy

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
    "magnetometer": [],
    "microphone": [],
    "payment": [],
    "usb": [],
}
