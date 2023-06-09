import contextlib
import http
from datetime import timedelta

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

from radiofeed.decorators import require_form_methods
from radiofeed.websub import signature, subscriber
from radiofeed.websub.models import Subscription


@require_form_methods
@csrf_exempt
@never_cache
def callback(request: HttpRequest, subscription_id: int) -> HttpResponse:
    """Callback view as per spec https://www.w3.org/TR/websub/.

    Handles GET and POST requests:

    1. A POST request is used for content distribution and indicates podcast should be updated with new content.

    2. A GET request is used for feed verification.
    """

    # content distribution
    if request.method == "POST":
        # always return a 204 regardless
        with contextlib.suppress(Subscription.DoesNotExist, signature.InvalidSignature):
            subscription = Subscription.objects.select_related("podcast").get(
                pk=subscription_id,
                mode=subscriber.SUBSCRIBE,
                podcast__active=True,
            )

            signature.check_signature(request, subscription.secret)

            # prioritize podcast for immediate update
            subscription.podcast.priority = True
            subscription.podcast.pinged = timezone.now()
            subscription.podcast.save()

        return HttpResponse(status=http.HTTPStatus.NO_CONTENT)

    # verification
    try:
        # check all required fields are present

        mode = request.GET["hub.mode"]
        topic = request.GET["hub.topic"]
        challenge = request.GET["hub.challenge"]

        lease_seconds = int(
            request.GET.get("hub.lease_seconds", subscriber.DEFAULT_LEASE_SECONDS)
        )

        subscription = get_object_or_404(Subscription, topic=topic, pk=subscription_id)

        subscription.mode = mode

        subscription.expires = (
            timezone.now() + timedelta(seconds=lease_seconds)
            if mode == subscriber.SUBSCRIBE
            else None
        )

        subscription.save()

        return HttpResponse(challenge)

    except (KeyError, ValueError) as e:
        raise Http404 from e
