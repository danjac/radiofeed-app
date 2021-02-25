from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_POST
from turbo_response import TurboStream

from radiofeed.shortcuts import render_component

from ..models import Podcast, Subscription
from .list_detail import get_podcast_or_404


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

    return TurboStream(podcast.dom.subscribe_toggle).replace.response(
        render_component(request, "subscribe_toggle", podcast, is_subscribed)
    )
