from __future__ import annotations

import uuid

from datetime import datetime

from django.db import models
from django.urls import reverse
from django.utils import timezone
from model_utils.models import TimeStampedModel

from jcasts.podcasts.models import Podcast
from jcasts.shared.template import build_absolute_uri


class Subscription(TimeStampedModel):
    class Status(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        SUBSCRIBED = "subscribed", "Subscribed"
        UNSUBSCRIBED = "unsubscribed", "Unsubscribed"
        DENIED = "denied", "Denied"

    id: uuid.UUID = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )

    podcast: Podcast = models.ForeignKey(Podcast, on_delete=models.CASCADE)

    hub: str = models.URLField(max_length=2086)
    topic: str = models.URLField(max_length=2086)

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        null=True,
        blank=True,
    )
    status_changed: datetime | None = models.DateTimeField(null=True, blank=True)

    secret: uuid.UUID = models.UUIDField(default=uuid.uuid4, editable=False)

    expires: datetime | None = models.DateTimeField(null=True, blank=True)

    exception: str = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s",
                fields=["podcast", "hub", "topic"],
            )
        ]

    def __str__(self) -> str:
        return self.topic

    def get_callback_url(self) -> str:
        return build_absolute_uri(reverse("websub:callback", args=[self.id]))

    def set_status(self, mode: str) -> str | None:
        self.status = {
            "subscribe": Subscription.Status.SUBSCRIBED,
            "unsubscribe": Subscription.Status.UNSUBSCRIBED,
            "denied": Subscription.Status.DENIED,
        }[mode]
        self.status_changed = timezone.now()
        return self.status  # type: ignore
