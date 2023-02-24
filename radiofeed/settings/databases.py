from __future__ import annotations

import dj_database_url

from radiofeed.settings.base import config


def configure_databases(*, conn_max_age: int) -> dict:
    """Build DATABASES configuration."""
    return {
        "default": {
            **dj_database_url.parse(
                config(
                    "DATABASE_URL",
                    default="postgresql://postgres:password@localhost:5432/postgres",
                ),
                conn_max_age=conn_max_age,
                conn_health_checks=conn_max_age > 0,
            ),
            "ATOMIC_REQUESTS": True,
        },
    }
