import contextlib
import http

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

from radiofeed.decorators import require_form_methods
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
        with contextlib.suppress(
            Subscription.DoesNotExist, Subscription.InvalidSignature
        ):
            subscription = Subscription.objects.select_related("podcast").get(
                pk=subscription_id,
                mode=Subscription.Mode.SUBSCRIBE,
                podcast__active=True,
            )

            subscription.check_signature(request)

            subscription.pinged = timezone.now()
            subscription.save()

            # prioritize podcast for immediate update
            subscription.podcast.priority = True
            subscription.podcast.save()

        return HttpResponse(status=http.HTTPStatus.NO_CONTENT)

    # verification
    try:
        # check all required fields are present

        mode = request.GET["hub.mode"]
        topic = request.GET["hub.topic"]
        challenge = request.GET["hub.challenge"]

        lease_seconds = int(
            request.GET.get("hub.lease_seconds", Subscription.DEFAULT_LEASE_SECONDS)
        )

        subscription = get_object_or_404(Subscription, topic=topic, pk=subscription_id)
        subscription.verify(mode, lease_seconds)

        return HttpResponse(challenge)

    except (KeyError, ValueError) as e:
        raise Http404 from e
