# Settings for local development and CI. Unsafe for production!

from __future__ import annotations

from radiofeed.settings.admin import admin_site_header
from radiofeed.settings.databases import configure_databases
from radiofeed.settings.templates import configure_templates

DEBUG = True

SECRET_KEY = (
    "django-insecure-+-pzc(vc+*=sjj6gx84da3y-2y@h_&f=)@s&fvwwpz_+8(ced^"  # nosec
)

HTTP_PROTOCOL = "http"

DATABASES = configure_databases(conn_max_age=0)

TEMPLATES = configure_templates(debug=True)

ADMIN_SITE_HEADER = admin_site_header("LOCAL")
