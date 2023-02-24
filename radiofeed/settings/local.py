from __future__ import annotations

from radiofeed.settings.common import configure_databases, configure_templates

DEBUG = True

DATABASES = configure_databases(conn_max_age=0)

TEMPLATES = configure_templates(debug=True)
