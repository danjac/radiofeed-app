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

DEBUG = False

SECRET_KEY = env("SECRET_KEY")

DATABASES = {
    "default": {
        **env.db(),
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": 360,
    },
}

# prevent deprecation warnings
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = env("REDIS_URL")

CACHES: dict = {
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

EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

CONTACT_EMAIL = env("CONTACT_EMAIL", default="admin@localhost")

ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS", default=[])

ADMINS = getaddresses(env.list("ADMINS", default=[]))

SITE_ID = 1

SESSION_COOKIE_DOMAIN = env("SESSION_COOKIE_DOMAIN", default=None)
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

CSRF_COOKIE_DOMAIN = env("CSRF_COOKIE_DOMAIN", default=None)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

ROOT_URLCONF = "radiofeed.urls"

INSTALLED_APPS: list[str] = [
    "django.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.postgres",
    "django.contrib.sitemaps",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "cacheops",
    "django_extensions",
    "django_htmx",
    "django_object_actions",
    "fast_update",
    "modeltranslation",
    "widget_tweaks",
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
    "django_htmx.middleware.HtmxMiddleware",
    "radiofeed.common.middleware.cache_control_middleware",
    "radiofeed.common.middleware.search_middleware",
    "radiofeed.common.middleware.sorter_middleware",
    "radiofeed.episodes.middleware.player_middleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "radiofeed.users.middleware.language_middleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# admin settings

ADMIN_SITE_HEADER = env("ADMIN_SITE_HEADER", default="Radiofeed Admin")

ADMIN_URL = env("ADMIN_URL", default="admin/")

# auth

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

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("fi", "Suomi"),
]
LANGUAGE_COOKIE_DOMAIN = env("LANGUAGE_COOKIE_DOMAIN", default=None)
LANGUAGE_COOKIE_SAMESITE = "Lax"

LOCALE_PATHS = [BASE_DIR / "i18n"]

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# https://docs.djangoproject.com/en/1.11/ref/forms/renderers/

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

STATIC_URL = env("STATIC_URL", default="/static/")
STATICFILES_DIRS = [BASE_DIR / "static"]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": DEBUG,
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

# https://docs.djangoproject.com/en/4.1/ref/contrib/messages/

MESSAGE_TAGS = {
    messages.DEBUG: "bg-gray-600",
    messages.ERROR: "bg-red-600",
    messages.INFO: "bg-blue-600",
    messages.SUCCESS: "bg-green-600",
    messages.WARNING: "bg-violet-600",
}

# https://github.com/Suor/django-cacheops

CACHEOPS_REDIS = REDIS_URL
CACHEOPS_DEFAULTS = {"timeout": 300}
CACHEOPS_DEGRADE_ON_FAILURE = True

CACHEOPS = {
    "podcasts.*": {"ops": "all"},
    "episodes.*": {"ops": "all"},
    "users.*": {"ops": "all"},
}

# Model translations
# https://django-modeltranslation.readthedocs.io/en/latest/installation.html#configuration

MODELTRANSLATION_DEFAULT_LANGUAGE = "en"
MODELTRANSLATION_FALLBACK_LANGUAGES = ("en",)


# Environments

ENVIRONMENT: Environments = env("ENVIRONMENT", default="development")

match ENVIRONMENT:

    case "development":

        DEBUG = True

        ADMIN_SITE_HEADER += " [LOCAL]"

        INSTALLED_APPS = [
            "whitenoise.runserver_nostatic",
            "debug_toolbar",
        ] + INSTALLED_APPS

        MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]

        INTERNAL_IPS = ["127.0.0.1"]

    case "test":

        LOGGING = None

        PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

        ALLOWED_HOSTS += [".example.com"]

        CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}

        CACHEOPS_ENABLED = False

        EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

        # django-coverage-plugin
        TEMPLATES[0]["OPTIONS"]["debug"] = True  # type: ignore

    case "production":

        ADMIN_SITE_HEADER += " [PRODUCTION]"

        STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
        STATIC_ROOT = BASE_DIR / "staticfiles"

        # Secure production settings

        SECURE_BROWSER_XSS_FILTER = True
        SECURE_CONTENT_TYPE_NOSNIFF = True
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True
        SECURE_HSTS_SECONDS = 15768001  # 6 months
        SECURE_SSL_REDIRECT = True

        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True

        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

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

        # Mailgun

        MAILGUN_API_KEY = env("MAILGUN_API_KEY", default=None)
        MAILGUN_SENDER_DOMAIN = env("MAILGUN_SENDER_DOMAIN", default=None)

        if MAILGUN_API_KEY and MAILGUN_SENDER_DOMAIN:

            INSTALLED_APPS += ["anymail"]

            EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"

            MAILGUN_API_URL = env(
                "MAILGUN_API_URL", default="https://api.mailgun.net/v3"
            )

            ANYMAIL = {
                "MAILGUN_API_KEY": MAILGUN_API_KEY,
                "MAILGUN_API_URL": MAILGUN_API_URL,
                "MAILGUN_SENDER_DOMAIN": MAILGUN_SENDER_DOMAIN,
            }

            SERVER_EMAIL = f"errors@{MAILGUN_SENDER_DOMAIN}"
            DEFAULT_FROM_EMAIL = f"support@{MAILGUN_SENDER_DOMAIN}"
