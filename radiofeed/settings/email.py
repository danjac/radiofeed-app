from __future__ import annotations

from radiofeed.settings.base import INSTALLED_APPS, config

# Email configuration

EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=1025, cast=int)

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Email sender addresses

SERVER_EMAIL = config("SERVER_EMAIL", default=f"errors@{EMAIL_HOST}")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default=f"no-reply@{EMAIL_HOST}")

# email shown in about page etc
CONTACT_EMAIL = config("CONTACT_EMAIL", default=f"support@{EMAIL_HOST}")

# Mailgun

# https://anymail.dev/en/v9.0/esps/mailgun/

if MAILGUN_API_KEY := config("MAILGUN_API_KEY", default=None):
    INSTALLED_APPS += ["anymail"]

    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"

    MAILGUN_API_URL = config("MAILGUN_API_URL", default="https://api.mailgun.net/v3")

    ANYMAIL = {
        "MAILGUN_API_KEY": MAILGUN_API_KEY,
        "MAILGUN_API_URL": MAILGUN_API_URL,
        "MAILGUN_SENDER_DOMAIN": EMAIL_HOST,
    }
