from __future__ import annotations

import contextlib
import http
import logging

from datetime import timedelta

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from radiofeed.decorators import require_form_methods
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.feedparser.feed_parser import FeedParser
from radiofeed.websub import subscriber
from radiofeed.websub.models import Subscription

logger = logging.getLogger(__name__)


@require_form_methods
@csrf_exempt
def websub_callback(request: HttpRequest, subscription_id: int) -> HttpResponse:
    """Callback view as per spec https://www.w3.org/TR/websub/.

    Handles GET and POST requests:

    1. A POST request is used for content distribution and indicates podcast should be updated with new content.

    2. A GET request is used for feed verification.
    """
    # content distribution

    qs = Subscription.objects.filter(pk=subscription_id)

    if request.method == "POST":
        subscription = get_object_or_404(qs.select_related("podcast"))

        if subscriber.check_signature(request, subscription):
            with contextlib.suppress(FeedParserError):
                FeedParser(subscription.podcast).parse()

        return HttpResponse(status=http.HTTPStatus.NO_CONTENT)

    # verification

    try:
        subscription = get_object_or_404(qs.filter(topic=request.GET["hub.topic"]))

        subscription.expires = (
            timezone.now() + timedelta(seconds=int(request.GET["hub.lease_seconds"]))
            if request.GET["hub.mode"] == "subscribe"
            else None
        )

        subscription.save()

        return HttpResponse(request.GET["hub.challenge"])

    except (KeyError, ValueError) as e:
        raise Http404 from e
