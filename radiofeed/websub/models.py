from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone
from model_utils.models import TimeStampedModel

from radiofeed.podcasts.models import Podcast


class SubscriptionQuerySet(models.QuerySet):
    """Custom QuerySet."""

    def for_subscribe(self) -> models.QuerySet[Subscription]:
        """Return subscriptions for websub subscription requests."""
        return self.filter(
            models.Q(
                mode="",
            )
            | models.Q(
                mode=self.model.Mode.SUBSCRIBE,
                # check any expiring within one hour
                expires__lt=timezone.now() + timedelta(hours=1),
            ),
            podcast__active=True,
            num_retries__lt=self.model.MAX_NUM_RETRIES,
        )


class Subscription(TimeStampedModel):
    """Websub subscription for a podcast."""

    DEFAULT_LEASE_SECONDS: int = 24 * 60 * 60 * 7  # 1 week
    MAX_NUM_RETRIES: int = 3

    class InvalidSignature(ValueError):
        """Raised if bad signature passed in Content Distribution call."""

    class Mode(models.TextChoices):
        SUBSCRIBE = "subscribe", "Subscribe"
        UNSUBSCRIBE = "unsubscribe", "Unsubscribe"

    podcast: Podcast = models.ForeignKey(
        "podcasts.Podcast",
        on_delete=models.CASCADE,
        related_name="websub_subscriptions",
    )

    hub: str = models.URLField(max_length=2086)
    topic: str = models.URLField(max_length=2086)

    mode: str = models.CharField(max_length=12, blank=True, choices=Mode.choices)
    secret: uuid.UUID | None = models.UUIDField(blank=True, null=True)

    expires: datetime | None = models.DateTimeField(null=True, blank=True)
    requested: datetime | None = models.DateTimeField(null=True, blank=True)
    verified: datetime | None = models.DateTimeField(null=True, blank=True)

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
        """Returns websub topic"""
        return self.topic

    def get_callback_url(self) -> str:
        """Returns url to websub callback hook."""
        return reverse("websub:callback", args=[self.pk])

    def subscribe(
        self,
        mode: str = Mode.SUBSCRIBE,  # type: ignore
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> requests.Response | None:
        """Subscribes podcast to provided websub hub.

        Raises:
            requests.RequestException: invalid request
        """
        secret = uuid.uuid4()

        scheme = "https" if settings.USE_HTTPS else "http"
        site = Site.objects.get_current()

        payload = {
            "hub.mode": mode,
            "hub.topic": self.topic,
            "hub.callback": f"{scheme}://{site.domain}{self.get_callback_url()}",
        }

        if mode == self.Mode.SUBSCRIBE:  # type: ignore
            payload = {
                **payload,
                "hub.secret": secret.hex,
                "hub.lease_seconds": str(lease_seconds),
            }

        try:
            response = requests.post(
                self.hub,
                payload,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": settings.USER_AGENT,
                },
                allow_redirects=True,
                timeout=10,
            )

            response.raise_for_status()

            self.mode = mode
            self.secret = secret if mode == self.Mode.SUBSCRIBE else None  # type: ignore
            self.requested = timezone.now()
            self.num_retries = 0

        except requests.RequestException:
            self.num_retries += 1
            raise
        finally:
            self.save()

        return response

    def verify(
        self,
        mode: str = Mode.SUBSCRIBE,  # type: ignore
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> None:
        """Handles the verification step."""

        now = timezone.now()

        self.mode = mode
        self.requested = None
        self.verified = now

        self.expires = (
            now + timedelta(seconds=lease_seconds)
            if self.mode == self.Mode.SUBSCRIBE  # type: ignore
            else None
        )
        self.save()

    def check_signature(
        self, request: HttpRequest, max_body_size: int = 1024**2
    ) -> None:
        """Check X-Hub-Signature header against the secret in database.

        Raises:
            InvalidSignature
        """

        if self.secret is None:
            raise self.InvalidSignature("secret is not set")

        try:
            content_length = int(request.headers["content-length"])
            algo, signature = request.headers["X-Hub-Signature"].split("=")
        except (KeyError, ValueError) as e:
            raise self.InvalidSignature("missing or invalid headers") from e

        if content_length > max_body_size:
            raise self.InvalidSignature("content length exceeds max body size")

        try:
            algo_method = getattr(hashlib, algo)
        except AttributeError as e:
            raise self.InvalidSignature(f"{algo} is not a valid algorithm") from e

        if not hmac.compare_digest(
            signature,
            hmac.new(
                self.secret.hex.encode("utf-8"),
                request.body,
                algo_method,
            ).hexdigest(),
        ):
            raise self.InvalidSignature("signature does not match")
