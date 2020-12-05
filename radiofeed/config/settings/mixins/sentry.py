import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from ..base import env

sentry_sdk.init(
    dsn=env("SENTRY_URL"),
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True,
)
