from __future__ import annotations

import hashlib
import hmac
import http
import traceback
import uuid

import attr
import requests

from django.db.models import Q
from django.http import HttpRequest
from django.utils import timezone
from django_rq import job

from jcasts.websub.models import Subscription

DEFAULT_LEASE_SECONDS = 24 * 60 * 60 * 7
MAX_BODY_SIZE = 1024 ** 2
MAX_REQUESTS = 3


@attr.s(kw_only=True)
class SubscribeResult:
    subscription_id: uuid.UUID = attr.ib()
    success: bool = attr.ib()
    status: int | None = attr.ib(default=None)
    exception: Exception | None = attr.ib(default=None)

    def __bool__(self) -> bool:
        return self.success


def enqueue(limit: int = 200) -> None:
    """Renew any expired subscriptions and any
    unverified new subscriptions"""

    for subscription_id in (
        Subscription.objects.filter(
            Q(
                status=Subscription.Status.SUBSCRIBED,
                expires__lt=timezone.now(),
            )
            | Q(
                status=None,
                requests__lt=MAX_REQUESTS,
            ),
        )
        .order_by("expires", "requested", "created")
        .values_list("pk", flat=True)
    )[:limit]:
        subscribe.delay(subscription_id, mode="subscribe")


@job("default")
def subscribe(
    subscription_id: uuid.UUID,
    mode: str = "subscribe",
) -> SubscribeResult:
    """Attempt to send a subscribe or other request to the hub."""

    try:
        subscription = Subscription.objects.get(pk=subscription_id)
    except Subscription.DoesNotExist as e:
        return SubscribeResult(
            subscription_id=subscription_id,
            exception=e,
            success=False,
        )

    response = requests.post(
        subscription.hub,
        {
            "hub.mode": mode,
            "hub.topic": subscription.topic,
            "hub.secret": subscription.secret.hex,
            "hub.callback": subscription.get_callback_url(),
            "hub.lease_seconds": DEFAULT_LEASE_SECONDS,
            # these two fields are not present in websub v4+
            # but keeping around for feeds using older hubs
            "hub.verify_token": subscription.id.hex,
            "hub.verify": "async",
        },
        timeout=10,
    )

    now = timezone.now()

    update_kwargs = {
        "modified": now,
        "requested": now,
        "requests": subscription.requests + 1,
    }

    try:
        response.raise_for_status()

        # a 202 indicates the hub will try to verify asynchronously
        # through a GET request to the websub callback url. Otherwise we can set
        # relevant status immediately.

        if response.status_code != http.HTTPStatus.ACCEPTED:
            update_kwargs = {
                **update_kwargs,
                "status": get_status_for_mode(mode),
                "status_changed": now,
            }

        return SubscribeResult(
            subscription_id=subscription.id,
            status=response.status_code,
            success=True,
        )

    except requests.RequestException as e:

        update_kwargs["exception"] = traceback.format_exc()

        return SubscribeResult(
            subscription_id=subscription.id,
            status=e.response.status_code if e.response else None,
            success=False,
            exception=e,
        )
    finally:
        Subscription.objects.filter(pk=subscription.id).update(**update_kwargs)


def check_signature(request: HttpRequest, subscription: Subscription) -> bool:

    try:
        if int(request.META["CONTENT_LENGTH"]) > MAX_BODY_SIZE:
            return False

        algo, signature = request.headers["X-Hub-Signature"].split("=")
        digest = hmac.new(
            subscription.secret.hex.encode("utf-8"),
            request.body,
            getattr(hashlib, algo),
        ).hexdigest()

    except (AttributeError, KeyError, ValueError):
        return False

    return hmac.compare_digest(signature, digest)


def get_status_for_mode(mode: str) -> str:
    return {
        "subscribe": Subscription.Status.SUBSCRIBED,
        "unsubscribe": Subscription.Status.UNSUBSCRIBED,
        "denied": Subscription.Status.DENIED,
    }[
        mode
    ]  # type: ignore
