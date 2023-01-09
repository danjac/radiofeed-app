from __future__ import annotations

from radiofeed.settings.base import TEMPLATES

DEBUG = True

for config in TEMPLATES:
    config["OPTIONS"]["debug"] = True  # type: ignore
