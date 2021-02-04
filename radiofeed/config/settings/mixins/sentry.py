import sentry_sdk
from sentry.integrations.logging import ignore_logger
from sentry_sdk.integrations.django import DjangoIntegration

from ..base import env

ignore_logger("django.security.DisallowedHost")

sentry_sdk.init(
    dsn=env("SENTRY_URL"),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.5,
    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True,
)
