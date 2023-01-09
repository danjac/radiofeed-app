from __future__ import annotations

from radiofeed.settings.base import *  # noqa

DEBUG = True

INSTALLED_APPS += [  # noqa
    "debug_toolbar",
    "django_browser_reload",
    "whitenoise.runserver_nostatic",
]

MIDDLEWARE += [  # noqa
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

TEMPLATES[0]["OPTIONS"]["debug"] = True  # type: ignore # noqa

ADMIN_SITE_HEADER += " [DEVELOPMENT]"  # noqa
