import pathlib
from email.utils import getaddresses

import sentry_sdk
from django.urls import reverse_lazy
from environs import Env
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger

BASE_DIR = pathlib.Path(__file__).resolve(strict=True).parents[1]

env = Env()
env.read_env()

DEBUG = env.bool("DEBUG", default=False)

SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-+-pzc(vc+*=sjj6gx84da3y-2y@h_&f=)@s&fvwwpz_+8(ced^",
)

SECRET_KEY_FALLBACKS = env.list("SECRET_KEY_FALLBACKS", default=[])

INSTALLED_APPS: list[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.humanize",
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
    "csp",
    "django_extensions",
    "django_htmx",
    "django_linear_migrations",
    "django_tailwind_cli",
    "django_typer",
    "django_version_checks",
    "health_check",
    "health_check.db",
    "health_check.cache",
    "health_check.contrib.migrations",
    "health_check.contrib.psutil",
    "health_check.contrib.redis",
    "heroicons",
    "widget_tweaks",
    # https://django-cotton.com/docs/django-template-partials
    "django_cotton.apps.SimpleAppConfig",
    "template_partials.apps.SimpleAppConfig",
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
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "csp.middleware.CSPMiddleware",
    "radiofeed.middleware.HtmxRestoreMiddleware",
    "radiofeed.middleware.HtmxMessagesMiddleware",
    "radiofeed.middleware.HtmxRedirectMiddleware",
    "radiofeed.middleware.SearchMiddleware",
    "radiofeed.episodes.middleware.PlayerMiddleware",
]

# Databases

DATABASES = {
    "default": env.dj_db_url(
        "DATABASE_URL",
        default="postgresql://postgres:password@127.0.0.1:5432/postgres",
    )
}

if env.bool("USE_CONNECTION_POOL", default=True):
    DATABASES["default"]["OPTIONS"] = {
        "pool": (
            {
                "min_size": env.int("CONN_POOL_MIN_SIZE", 2),
                "max_size": env.int("CONN_POOL_MAX_SIZE", 100),
                "max_lifetime": env.int("CONN_POOL_MAX_LIFETIME", 1800),
                "max_idle": env.int("CONN_POOL_MAX_IDLE", 300),
                "max_waiting": env.int("CONN_POOL_MAX_WAITING", 25),
                "timeout": env.int("CONN_POOL_TIMEOUT", default=5),
            }
        ),
    }
else:
    DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=0)


# Caches

CACHES = {
    "default": env.dj_cache_url("REDIS_URL", default="redis://127.0.0.1:6379/0")
    | {
        "TIMEOUT": 300,
    }
}


# Required for health check
REDIS_URL = CACHES["default"]["LOCATION"]

# Templates

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "OPTIONS": {
            "builtins": [
                "django_cotton.templatetags.cotton",
                "radiofeed.templatetags",
            ],
            "debug": env.bool("TEMPLATE_DEBUG", default=False),
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "radiofeed.context_processors.csrf_header",
            ],
            # https://django-cotton.com/docs/django-template-partials
            "loaders": [
                (
                    "template_partials.loader.Loader",
                    [
                        (
                            "django.template.loaders.cached.Loader",
                            [
                                "django_cotton.cotton_loader.Loader",
                                "django.template.loaders.filesystem.Loader",
                                "django.template.loaders.app_directories.Loader",
                            ],
                        )
                    ],
                )
            ],
        },
    }
]

# https://django-cotton.com/docs/configuration

COTTON_DIR = "components"

# prevent deprecation warnings
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Server settings

ROOT_URLCONF = "config.urls"

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

SITE_ID = 1

# Session and cookies

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

CSRF_USE_SESSIONS = True

CSRF_TRUSTED_ORIGINS = [
    f"{scheme}://{host}"
    for host in env.list("CSRF_TRUSTED_ORIGINS", default=[]) or []
    for scheme in ["http", "https"]
]

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True


# Email configuration

# Mailgun
# https://anymail.dev/en/v9.0/esps/mailgun/

if MAILGUN_API_KEY := env("MAILGUN_API_KEY", default=None):
    INSTALLED_APPS += ["anymail"]

    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"

    # For European domains: https://api.eu.mailgun.net/v3
    MAILGUN_API_URL = env("MAILGUN_API_URL", default="https://api.mailgun.net/v3")
    MAILGUN_SENDER_DOMAIN = EMAIL_HOST = env("MAILGUN_SENDER_DOMAIN")

    ANYMAIL = {
        "MAILGUN_API_KEY": MAILGUN_API_KEY,
        "MAILGUN_API_URL": MAILGUN_API_URL,
        "MAILGUN_SENDER_DOMAIN": MAILGUN_SENDER_DOMAIN,
    }
else:
    EMAIL_CONFIG = env.dj_email_url("EMAIL_URL", default="smtp://localhost:1025")

    EMAIL_HOST = EMAIL_CONFIG["EMAIL_HOST"]

    vars().update(EMAIL_CONFIG)

    EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)

ADMINS = getaddresses([admins]) if (admins := env("ADMINS", default="")) else []

MANAGERS = (
    getaddresses([managers]) if (managers := env("MANAGERS", default="")) else ADMINS
)

SERVER_EMAIL = env("SERVER_EMAIL", default=f"no-reply@{EMAIL_HOST}")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=SERVER_EMAIL)
CONTACT_EMAIL = env("CONTACT_EMAIL", default=SERVER_EMAIL)

# authentication settings
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends

AUTH_USER_MODEL = "users.User"

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

LOGIN_REDIRECT_URL = reverse_lazy("podcasts:subscriptions")
LOGIN_URL = reverse_lazy("account_login")

# https://django-allauth.readthedocs.io/en/latest/configuration.html

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_PREVENT_ENUMERATION = False
ACCOUNT_UNIQUE_EMAIL = True

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

# admin settings

ADMIN_URL = env("ADMIN_URL", default="admin/")
ADMIN_SITE_HEADER = env("ADMIN_SITE_HEADER", default="Radiofeed Admin")

# Internationalization/Localization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = "en"

USE_TZ = True
TIME_ZONE = "UTC"

USE_I18N = False

FORMAT_MODULE_PATH = ["config.formats"]

# Static files

STATIC_URL = env("STATIC_URL", default="/static/")
STATIC_SRC = BASE_DIR / "static"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [STATIC_SRC]

# Tailwind CLI
# https://django-tailwind-cli.andrich.me/settings/#settings

TAILWIND_CLI_SRC_CSS = BASE_DIR / "tailwind" / "app.css"
TAILWIND_CLI_DIST_CSS = "app.css"
TAILWIND_CLI_VERSION = "4.0.0"

# Whitenoise
# https://whitenoise.readthedocs.io/en/latest/django.html
#

if env.bool("USE_COLLECTSTATIC", default=True):
    STORAGES = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    # for development only
    INSTALLED_APPS += ["whitenoise.runserver_nostatic"]


# Templates
# https://docs.djangoproject.com/en/1.11/ref/forms/renderers/

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# Secure settings
# https://docs.djangoproject.com/en/4.1/topics/security/

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

if USE_X_FORWARDED_HOST := env.bool("USE_X_FORWARDED_HOST", default=True):
    SECURE_PROXY_SSL_HEADER = tuple(
        env.list(
            "SECURE_PROXY_SSL_HEADER",
            default=["HTTP_X_FORWARDED_PROTO", "https"],
        )
        or []
    )

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)

SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False
)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)

# Permissions Policy
# https://pypi.org/project/django-permissions-policy/

PERMISSIONS_POLICY: dict[str, list] = {
    "accelerometer": [],
    "camera": [],
    "encrypted-media": [],
    "fullscreen": [],
    "geolocation": [],
    "gyroscope": [],
    "magnetometer": [],
    "microphone": [],
    "payment": [],
}

# Content-Security-Policy
# https://django-csp.readthedocs.io/en/3.8/configuration.html

SELF = "'self'"
DATA = f"data: {'https' if SECURE_SSL_REDIRECT else 'http'}:;"
UNSAFE_EVAL = "'unsafe-eval'"
UNSAFE_INLINE = "'unsafe-inline'"

CSP_DEFAULT_SRC = [SELF]

CSP_SCRIPT_SRC = [
    SELF,
    UNSAFE_EVAL,
    UNSAFE_INLINE,
    *(env.list("CSP_SCRIPT_WHITELIST", default=[]) or []),
]

CSP_STYLE_SRC = [SELF, UNSAFE_INLINE]

CSP_IMG_SRC = [f" * {SELF} {DATA}"]

# Allow all audio files
CSP_MEDIA_SRC = ["*"]

# Logging
# https://docs.djangoproject.com/en/5.0/howto/logging/

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
        },
        "null": {
            "level": "DEBUG",
            "class": "logging.NullHandler",
        },
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
            "handlers": ["console"],
            "propagate": False,
        },
        "environ": {
            "handlers": ["console"],
            "level": "CRITICAL",
            "propagate": False,
        },
        "httpx": {
            "handlers": ["console"],
            "level": "CRITICAL",
            "propagate": False,
        },
        "httpcore": {
            "handlers": ["console"],
            "level": "CRITICAL",
            "propagate": False,
        },
    },
}

# Sentry
# https://docs.sentry.io/platforms/python/guides/django/

if SENTRY_URL := env("SENTRY_URL", default=None):
    ignore_logger("django.security.DisallowedHost")

    sentry_sdk.init(
        dsn=SENTRY_URL,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.5,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
    )

# Health checks

# https://pypi.org/project/django-version-checks/

VERSION_CHECKS = {
    "postgresql": "~=16.2",
    "python": "==3.13.*",
}

# https://pypi.org/project/django-health-check/

HEALTH_CHECK = {
    "DISK_USAGE_MAX": 90,  # percent
    "MEMORY_MIN": 100,  # in MB
}

# Dev tools

# Django browser reload
# https://github.com/adamchainz/django-browser-reload

if env.bool("USE_BROWSER_RELOAD", default=False):
    INSTALLED_APPS += ["django_browser_reload"]

    MIDDLEWARE += ["django_browser_reload.middleware.BrowserReloadMiddleware"]

# Debug toolbar
# https://github.com/jazzband/django-debug-toolbar

if env.bool("USE_DEBUG_TOOLBAR", default=False):
    INSTALLED_APPS += ["debug_toolbar"]

    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]

    DEBUG_TOOLBAR_CONFIG = {"ROOT_TAG_EXTRA_ATTRS": "hx-preserve"}

    # INTERNAL_IPS required for debug toolbar
    INTERNAL_IPS = env.list("INTERNAL_IPS", default=["127.0.0.1"])

# PROJECT-SPECIFIC SETTINGS

# Cookie used to check user accepts cookies

GDPR_COOKIE_NAME = "accept-cookies"

# User-Agent header for API calls from this site

USER_AGENT = env("USER_AGENT", default="Radiofeed/0.0.0")

# Default page size for paginated views

DEFAULT_PAGE_SIZE = 30

# HTMX configuration
# https://htmx.org/docs/#config

HTMX_CONFIG = {
    "historyCacheSize": 0,
    "refreshOnHistoryMiss": False,
    "scrollBehavior": "instant",
    "scrollIntoViewOnBoost": False,
    "useTemplateFragments": True,
}

# PWA configuration
# https://docs.pwabuilder.com/#/builder/manifest
# https://developer.chrome.com/docs/android/trusted-web-activity/android-for-web-devs#digital-asset-links

PWA_CONFIG = {
    "assetlinks": {
        "package_name": env("PWA_PACKAGE_NAME", default="app.radiofeed.twa"),
        "sha256_fingerprints": env.list("PWA_SHA256_FINGERPRINTS", default=[]),
    },
    "manifest": {
        "categories": env.list(
            "PWA_CATEGORIES",
            default=[
                "books",
                "education",
                "entertainment",
                "news",
                "politics",
                "sport",
            ],
        ),
        "description": env("PWA_DESCRIPTION", default="Podcast aggregator site"),
        "background_color": env("PWA_BACKGROUND_COLOR", default="#FFFFFF"),
        "theme_color": env("PWA_THEME_COLOR", default="#26323C"),
    },
}
