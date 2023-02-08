from __future__ import annotations

import urllib
import uuid

from datetime import datetime

from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.urls import reverse
from model_utils.models import TimeStampedModel

from radiofeed.podcasts.models import Podcast


class Subscription(TimeStampedModel):
    """Websub subscription model."""

    podcast = models.ForeignKey(
        Podcast, on_delete=models.CASCADE, related_name="websub_subscriptions"
    )

    hub: str = models.URLField(max_length=2086)
    topic: str = models.URLField(max_length=2086)
    secret: uuid.UUID = models.UUIDField(default=uuid.uuid4, editable=False)

    mode: str = models.CharField(max_length=12, blank=True)

    expires: datetime | None = models.DateTimeField(null=True, blank=True)
    requested: datetime | None = models.DateTimeField(null=True, blank=True)
    verified: datetime | None = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s",
                fields=["podcast", "hub", "topic"],
            )
        ]

    def __str__(self) -> str:
        """Returns topic URL."""
        return self.topic

    def get_callback_url(self) -> str:
        """Return absolute URL to websub callback view."""
        return urllib.parse.urljoin(
            f"{settings.HTTP_PROTOCOL}://{Site.objects.get_current().domain}",
            reverse("websub:callback", args=[self.pk]),
        )
