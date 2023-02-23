from __future__ import annotations

from radiofeed.settings.base import *  # noqa
from radiofeed.settings.base import (
    ADMIN_SITE_HEADER,
    configure_databases,
    configure_templates,
)

DEBUG = True

DATABASES = configure_databases(conn_max_age=0)

TEMPLATES = configure_templates(debug=True)

ADMIN_SITE_HEADER += " [LOCAL]"
