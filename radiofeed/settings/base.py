from __future__ import annotations

import pathlib

from email.utils import getaddresses

import environ

from django.contrib.messages import constants as messages
from django.urls import reverse_lazy

BASE_DIR = pathlib.Path(__file__).resolve(strict=True).parents[2]

env = environ.Env()

env.read_env(BASE_DIR / ".env")

DEBUG = False

SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-+-pzc(vc+*=sjj6gx84da3y-2y@h_&f=)@s&fvwwpz_+8(ced^",
)


REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

# prevent deprecation warnings
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Server settings

ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS", default=[])

SITE_ID = 1

# Session and cookies

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

SESSION_COOKIE_DOMAIN = env("SESSION_COOKIE_DOMAIN", default=None)

CSRF_COOKIE_DOMAIN = env("CSRF_COOKIE_DOMAIN", default=None)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Email configuration

EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

ADMINS = getaddresses(env.list("ADMINS", default=[]))

SERVER_EMAIL = f"errors@{EMAIL_HOST}"
DEFAULT_FROM_EMAIL = f"no-reply@{EMAIL_HOST}"

# email shown in about page etc
CONTACT_EMAIL = env("CONTACT_EMAIL", default=f"admin@{EMAIL_HOST}")

ROOT_URLCONF = "radiofeed.urls"

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
    "cacheops",
    "django_extensions",
    "django_htmx",
    "django_object_actions",
    "fast_update",
    "widget_tweaks",
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
    "radiofeed.common.middleware.cache_control_middleware",
    "radiofeed.common.middleware.search_middleware",
    "radiofeed.common.middleware.sorter_middleware",
    "radiofeed.common.middleware.user_agent_middleware",
    "radiofeed.episodes.middleware.player_middleware",
]

# admin settings

ADMIN_URL = env("ADMIN_URL", default="admin/")

ADMIN_SITE_HEADER = env("ADMIN_SITE_HEADER", default="Radiofeed Admin")

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

CACHES: dict = {
    "default": {
        **env.cache("REDIS_URL", default=REDIS_URL),
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

CACHEOPS_REDIS = REDIS_URL
CACHEOPS_DEFAULTS = {"timeout": 300}
CACHEOPS_DEGRADE_ON_FAILURE = True

CACHEOPS = {
    "podcasts.*": {"ops": "all"},
    "episodes.*": {"ops": "all"},
    "users.*": {"ops": "all"},
}

# Databases


def configure_databases(conn_max_age: int = 360) -> dict:
    """Build DATABASES configuration."""
    return {
        "default": {
            **env.db(),
            "ATOMIC_REQUESTS": True,
            "CONN_MAX_AGE": conn_max_age,
        },
    }


DATABASES = configure_databases()

# Templates


def configure_templates(debug: bool = False) -> list[dict]:
    """Build TEMPLATES configuration."""
    return [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [BASE_DIR / "templates"],
            "APP_DIRS": True,
            "OPTIONS": {
                "debug": debug,
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


TEMPLATES = configure_templates()
