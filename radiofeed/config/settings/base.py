import pathlib
import socket

from email.utils import getaddresses

import environ

from django.urls import reverse_lazy

BASE_DIR = pathlib.Path(__file__).resolve(strict=True).parents[3]

env = environ.Env()


DEBUG = False

SECRET_KEY = env("SECRET_KEY")

DATABASES = {
    "default": {
        **env.db(),
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": 60,
    },
}

# prevent deprecation warnings
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = env("REDIS_URL")


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


DEFAULT_CACHE_TIMEOUT = 3600  # 1 hour

SOLO_CACHE = "default"
SOLO_CACHE_TIMEOUT = DEFAULT_CACHE_TIMEOUT


# https://huey.readthedocs.io/en/latest/django.html

HUEY = {
    "connection": {"url": REDIS_URL},
    "immediate": False,
}

EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# configure internal IPS inside docker container

INTERNAL_IPS = [
    ip[:-1] + "1" for ip in socket.gethostbyname_ex(socket.gethostname())[2]
]

ADMINS = getaddresses(env.list("ADMINS", default=[]))

SITE_ID = 1

SESSION_COOKIE_DOMAIN = env("SESSION_COOKIE_DOMAIN", default=None)
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

CSRF_COOKIE_DOMAIN = env("CSRF_COOKIE_DOMAIN", default=None)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

ROOT_URLCONF = "radiofeed.config.urls"

INSTALLED_APPS = [
    "postgres_metrics.apps.PostgresMetrics",
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
    "allauth.socialaccount.providers.twitter",
    "cachalot",
    "django_countries",
    "django_extensions",
    "django_htmx",
    "django_object_actions",
    "health_check",
    "health_check.cache",
    "health_check.contrib.migrations",
    "health_check.contrib.psutil",
    "health_check.contrib.redis",
    "health_check.db",
    "huey.contrib.djhuey",
    "solo",
    "widget_tweaks",
    "radiofeed.episodes",
    "radiofeed.podcasts",
    "radiofeed.settings",
    "radiofeed.users",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django_permissions_policy.PermissionsPolicyMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "radiofeed.common.middleware.CacheControlMiddleware",
    "radiofeed.common.middleware.SearchMiddleware",
    "radiofeed.episodes.middleware.PlayerMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

DEFAULT_PAGE_SIZE = 30

ADMIN_SITE_HEADER = "Radiofeed Admin"

# base Django admin URL (should be something obscure in production)

ADMIN_URL = env("ADMIN_URL", default="admin/")

# auth

AUTH_USER_MODEL = "users.User"

# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"  # noqa
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

HOME_URL = LOGIN_REDIRECT_URL = reverse_lazy("podcasts:index")

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
    ("en", "English (US)"),
    ("en-gb", "English (GB)"),
]
LANGUAGE_COOKIE_DOMAIN = env("LANGUAGE_COOKIE_DOMAIN", default=None)
LANGUAGE_COOKIE_SAMESITE = "Lax"

LOCALE_PATHS = [BASE_DIR / "i18n"]

TIME_ZONE = "UTC"

USE_I18N = False

USE_TZ = True

# https://docs.djangoproject.com/en/1.11/ref/forms/renderers/

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

STATIC_URL = env("STATIC_URL", default="/static/")
STATICFILES_DIRS = [BASE_DIR / "static"]

TEMPLATES: list[dict] = [
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


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "null": {"level": "DEBUG", "class": "logging.NullHandler"},
    },
    "loggers": {
        "root": {"handlers": ["console"], "level": "INFO"},
        "django.security.DisallowedHost": {"handlers": ["null"], "propagate": False},
        "django.request": {"handlers": ["console"], "level": "ERROR"},
        "radiofeed.podcasts.tasks": {"handlers": ["console"], "level": "DEBUG"},
    },
}
