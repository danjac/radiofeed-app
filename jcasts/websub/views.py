from __future__ import annotations

import traceback
import uuid

from datetime import timedelta

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from jcasts.podcasts import feed_parser
from jcasts.shared.response import HttpResponseNoContent
from jcasts.websub import subscriber
from jcasts.websub.models import Subscription


@require_http_methods(["GET", "POST"])
@csrf_exempt
def websub_callback(request: HttpRequest, subscription_id: uuid.UUID) -> HttpResponse:

    subscription = get_object_or_404(
        Subscription.objects.filter(podcast__active=True),
        pk=subscription_id,
    )

    # content distribution

    if request.method == "POST":

        if subscriber.check_signature(request, subscription):
            feed_parser.enqueue(subscription.podcast_id, url=subscription.topic)

        # always return a 2xx even on error so to prevent brute-force attacks
        return HttpResponseNoContent()

    # verification

    try:
        mode = request.GET["hub.mode"]
        challenge = request.GET["hub.challenge"]
        topic = request.GET["hub.topic"]

        if topic != subscription.topic:
            raise ValueError(
                f"{topic} does not match subscription topic {subscription.topic}"
            )

        now = timezone.now()

        if mode == "subscribe":
            subscription.expires = now + timedelta(
                seconds=int(request.GET["hub.lease_seconds"])
            )

        subscription.set_status(mode)

        return HttpResponse(challenge)

    except (KeyError, ValueError):
        subscription.exception = traceback.format_exc()
        raise Http404

    finally:
        subscription.save()
