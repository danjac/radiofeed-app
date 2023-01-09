from __future__ import annotations

import sentry_sdk

from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger

from radiofeed.settings.base import env

if SENTRY_URL := env("SENTRY_URL", default=None):  # noqa

    ignore_logger("django.security.DisallowedHost")

    sentry_sdk.init(
        dsn=SENTRY_URL,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.5,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
    )
