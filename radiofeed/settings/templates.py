from __future__ import annotations

from radiofeed.settings.base import BASE_DIR

# Templates


def configure_templates(*, debug: bool = False) -> list[dict]:
    """Build TEMPLATES configuration."""
    return [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [BASE_DIR / "templates"],
            "APP_DIRS": True,
            "OPTIONS": {
                "debug": debug,
                "context_processors": [
                    "django.template.context_processors.debug",
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.template.context_processors.i18n",
                    "django.template.context_processors.media",
                    "django.template.context_processors.static",
                    "django.template.context_processors.tz",
                    "django.contrib.messages.context_processors.messages",
                ],
                "builtins": [
                    "radiofeed.template",
                ],
            },
        }
    ]
