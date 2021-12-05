import http
import traceback
import uuid

import attr
import requests

from django.db.models import Q
from django.utils import timezone
from django_rq import job

from jcasts.websub.models import Subscription

DEFAULT_LEASE_SECONDS = 24 * 60 * 60 * 7


@attr.s(kw_only=True)
class SubscribeResult:
    subscription_id: uuid.UUID = attr.ib()
    success: bool = attr.ib()
    status: int | None = attr.ib(default=None)
    result: int | None = attr.ib(default=None)
    exception: Exception | None = attr.ib(default=None)


def renew():
    """Check any expired subscriptions and attempt to re-subscribe. This can be run
    in a cronjob."""

    for subscription in Subscription.objects.filter(
        status=Subscription.Status.SUBSCRIBED, expires__lt=timezone.now()
    ):
        subscribe.delay(subscription.id, mode="subscribe")


@job("default")
def subscribe(
    subscription_id: uuid.UUID,
    mode: str = "subscribe",
) -> SubscribeResult:
    """Attempt to send a subscribe or other request to the hub."""

    now = timezone.now()

    qs = Subscription.objects.filter(podcast__active=True)

    if mode == "subscribe":
        qs = qs.filter(
            Q(status=Subscription.Status.PENDING)
            | Q(status=Subscription.Status.SUBSCRIBED, expires__lt=now)
        )

    try:
        subscription = qs.get(pk=subscription_id)
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
        },
    )

    try:
        response.raise_for_status()

        subscription.status = (
            Subscription.Status.REQUESTED
            if response.status_code == http.HTTPStatus.ACCEPTED
            else {
                "subscribe": Subscription.Status.SUBSCRIBED,
                "unsubscribe": Subscription.Status.UNSUBSCRIBED,
                "denied": Subscription.Status.DENIED,
            }[mode]
        )
        subscription.status_changed = now

    except requests.RequestException as e:

        subscription.exception = traceback.format_exc()

        return SubscribeResult(
            subscription_id=subscription.id,
            result=e.response.status_code if e.response else None,
            success=False,
            exception=e,
        )
    finally:
        subscription.save()

    return SubscribeResult(
        subscription_id=subscription.id,
        result=response.status_code,
        success=True,
    )
