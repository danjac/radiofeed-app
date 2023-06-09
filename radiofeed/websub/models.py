from __future__ import annotations

import uuid
from datetime import datetime

from django.db import models
from django.urls import reverse
from model_utils.models import TimeStampedModel

from radiofeed.fast_count import FastCountQuerySetMixin
from radiofeed.podcasts.models import Podcast
from radiofeed.search import SearchQuerySetMixin


class SubscriptionQuerySet(
    FastCountQuerySetMixin, SearchQuerySetMixin, models.QuerySet
):
    """QuerySet for Subscription model."""

    search_vectors = [
        ("podcast__search_vector", "rank"),
    ]


class Subscription(TimeStampedModel):
    """Websub subscription for a podcast."""

    podcast: Podcast = models.ForeignKey(
        "podcasts.Podcast",
        on_delete=models.CASCADE,
        related_name="websub_subscriptions",
    )

    hub: str = models.URLField(max_length=2086)
    topic: str = models.URLField(max_length=2086)

    mode: str = models.CharField(max_length=12, blank=True)
    secret: uuid.UUID | None = models.UUIDField(blank=True, null=True)

    expires: datetime | None = models.DateTimeField(null=True, blank=True)
    confirmed: datetime | None = models.DateTimeField(null=True, blank=True)
    pinged: datetime | None = models.DateTimeField(null=True, blank=True)

    num_retries: int = models.PositiveSmallIntegerField(default=0)

    objects: models.Manager[Subscription] = SubscriptionQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_%(app_label)s_%(class)s_websub_podcast",
                fields=["podcast", "hub"],
            )
        ]

    def __str__(self) -> str:
        """Returns websub podcast"""
        return str(self.podcast)

    def get_callback_url(self) -> str:
        """Returns url to websub callback url."""
        return reverse("websub:callback", args=[self.pk])
