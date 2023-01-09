from __future__ import annotations

from split_settings.tools import include

from radiofeed.settings.base import ADMIN_SITE_HEADER, BASE_DIR

include("base.py")
include("mailgun.py")
include("secure.py")
include("sentry.py")
include("templates.py")

ADMIN_SITE_HEADER += " [PRODUCTION]"

# Static files

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_ROOT = BASE_DIR / "staticfiles"
