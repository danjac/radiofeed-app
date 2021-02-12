from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_POST

from turbo_response import TurboStream, TurboStreamResponse

from radiofeed.streams import (
    render_close_modal,
    render_info_message,
    render_success_message,
)

from ..models import Podcast, Subscription
from . import get_podcast_or_404


@require_POST
@login_required
def subscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:
    podcast = get_podcast_or_404(podcast_id)
    try:
        Subscription.objects.create(user=request.user, podcast=podcast)
    except IntegrityError:
        pass
    return render_subscribe_response(request, podcast, True)


@require_POST
@login_required
def unsubscribe(request: HttpRequest, podcast_id: int) -> HttpResponse:
    podcast = get_podcast_or_404(podcast_id)
    Subscription.objects.filter(podcast=podcast, user=request.user).delete()
    return render_subscribe_response(request, podcast, False)


def render_subscribe_response(
    request: HttpRequest, podcast: Podcast, is_subscribed: bool
) -> HttpResponse:
    streams = [
        TurboStream(podcast.get_subscribe_toggle_id())
        .replace.template(
            "podcasts/_subscribe.html",
            {"podcast": podcast, "is_subscribed": is_subscribed},
            request=request,
        )
        .render(),
        render_close_modal(),
    ]

    if is_subscribed:
        streams += [render_success_message("You are now subscribed to this podcast")]
    else:
        streams += [render_info_message("You are no longer subscribed to this podcast")]

    return TurboStreamResponse(streams)
