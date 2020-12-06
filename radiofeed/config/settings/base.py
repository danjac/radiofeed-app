# Standard Library
import pathlib
import socket
from email.utils import getaddresses

# Django
from django.contrib import messages

# Third Party Libraries
import environ

env = environ.Env()

DEBUG = False

BASE_DIR = pathlib.Path("/app")

SECRET_KEY = env("SECRET_KEY")

DATABASES = {
    "default": env.db(),
}

REDIS_URL = env("REDIS_URL")

CACHES = {"default": env.cache("REDIS_URL")}

EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_BACKEND = "djcelery_email.backends.CeleryEmailBackend"

ATOMIC_REQUESTS = True

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# configure internal IPS inside docker container

INTERNAL_IPS = [
    ip[:-1] + "1" for ip in socket.gethostbyname_ex(socket.gethostname())[2]
]

ADMINS = getaddresses(env.list("ADMINS", default=[]))

SESSION_COOKIE_DOMAIN = env("SESSION_COOKIE_DOMAIN", default=None)
CSRF_COOKIE_DOMAIN = env("CSRF_COOKIE_DOMAIN", default=None)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

ROOT_URLCONF = "radiofeed.config.urls"
WSGI_APPLICATION = "radiofeed.config.wsgi.application"

LOCAL_APPS = [
    "radiofeed.episodes.apps.EpisodesConfig",
    "radiofeed.podcasts.apps.PodcastsConfig",
    "radiofeed.users.apps.UsersConfig",
]


INSTALLED_APPS = [
    "django.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.postgres",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "django_extensions",
    "djcelery_email",
    "widget_tweaks",
    "sorl.thumbnail",
] + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "radiofeed.common.middleware.turbolinks.TurbolinksMiddleware",
    "radiofeed.common.middleware.ajax.AjaxRequestFragmentMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "radiofeed.common.middleware.http.HttpResponseNotAllowedMiddleware",
]

DEFAULT_PAGE_SIZE = 12

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

HOME_URL = LOGIN_REDIRECT_URL = "/"

LOGIN_URL = "account_login"

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "username_email"

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email",],
        "AUTH_PARAMS": {"access_type": "online",},
    }
}

SOCIALACCOUNT_ADAPTER = "radiofeed.users.adapters.SocialAccountAdapter"

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

USE_I18N = True

USE_L10N = True

USE_TZ = True

# https://docs.djangoproject.com/en/1.11/ref/forms/renderers/

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# https://docs.djangoproject.com/en/3.0/ref/contrib/messages/

MESSAGE_TAGS = {
    messages.DEBUG: "message-debug",
    messages.INFO: "message-info",
    messages.SUCCESS: "message-success",
    messages.WARNING: "message-warning",
    messages.ERROR: "message-error",
}

# https://celery.readthedocs.io/en/latest/userguide/configuration.html
result_backend = CELERY_BROKER_URL = REDIS_URL
result_serializer = "json"

# https://django-taggit.readthedocs.io/en/latest/getting_started.html

MEDIA_URL = env("MEDIA_URL", default="/media/")
STATIC_URL = env("STATIC_URL", default="/static/")

MEDIA_ROOT = BASE_DIR / "media"
STATICFILES_DIRS = [BASE_DIR / "static"]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": False,
            "builtins": [],
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
            "libraries": {
                "pagination": "radiofeed.common.pagination.templatetags",
                "html": "radiofeed.common.html.templatetags",
            },
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
    },
}
