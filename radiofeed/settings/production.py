from __future__ import annotations

from split_settings.tools import include

from radiofeed.settings.admin import admin_site_header
from radiofeed.settings.base import BASE_DIR
from radiofeed.settings.databases import configure_databases
from radiofeed.settings.templates import configure_templates

include(
    "base.py",
    "cache.py",
    "email.py",
    "logging.py",
    "secure.py",
)

DATABASES = configure_databases(conn_max_age=360)

TEMPLATES = configure_templates(debug=False)

ADMIN_SITE_HEADER = admin_site_header("PRODUCTION")

# Set HTTPS for absolute uris in allauth and our own absolute links

HTTP_PROTOCOL = ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"

# Static files

# http://whitenoise.evans.io/en/stable/django.html

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

STATIC_ROOT = BASE_DIR / "staticfiles"
