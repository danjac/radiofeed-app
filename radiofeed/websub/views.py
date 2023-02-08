from __future__ import annotations

import http
import logging
import traceback

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
    subscription = get_object_or_404(
        Subscription.objects.select_related("podcast"), pk=subscription_id
    )

    # content distribution

    if request.method == "POST":
        if subscriber.check_signature(request, subscription):
            try:
                FeedParser(subscription.podcast).parse()
            except FeedParserError:
                subscription.exception = traceback.format_exc()

        return HttpResponse(status_code=http.HTTPStatus.NO_CONTENT)

    # verification

    try:
        if request.GET["hub.topic"] != subscription.topic:
            raise ValueError("topic mismatch")

        subscription.set_status_for_mode(request.GET["hub.mode"])

        subscription.expires = timezone.now() + timedelta(
            seconds=int(request.GET["hub.lease_seconds"])
        )

        return HttpResponse(request.GET["hub.challenge"])

    except (KeyError, ValueError) as e:
        subscription.exception = traceback.format_exc()
        raise Http404 from e

    finally:
        subscription.save()
