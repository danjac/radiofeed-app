from __future__ import annotations

from split_settings.tools import include

# include all commonly used settings

include(
    "base.py",
    "admin.py",
    "email.py",
    "cache.py",
    "logging.py",
)
