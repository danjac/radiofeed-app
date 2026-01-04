from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST, require_safe

from simplecasts.http.decorators import require_DELETE
from simplecasts.http.request import AuthenticatedHttpRequest, HttpRequest
from simplecasts.http.response import HttpResponseConflict
from simplecasts.models import Podcast
from simplecasts.services.search import search_queryset
from simplecasts.views.paginator import render_paginated_response


@require_safe
@login_required
def index(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """Render podcast index page."""
    podcasts = Podcast.objects.published().subscribed(request.user).distinct()

    if request.search:
        podcasts = search_queryset(
            podcasts,
            request.search.value,
            "search_vector",
        ).order_by("-rank", "-pub_date")
    else:
        podcasts = podcasts.order_by("-pub_date")

    return render_paginated_response(request, "subscriptions/index.html", podcasts)


@require_POST
@login_required
def subscribe(
    request: AuthenticatedHttpRequest, podcast_id: int
) -> TemplateResponse | HttpResponseConflict:
    """Subscribe a user to a podcast. Podcast must be active and public."""
    podcast = get_object_or_404(
        Podcast.objects.published().filter(private=False), pk=podcast_id
    )

    try:
        request.user.subscriptions.create(podcast=podcast)
    except IntegrityError:
        return HttpResponseConflict()

    messages.success(request, "Subscribed to Podcast")

    return _render_subscribe_action(request, podcast, is_subscribed=True)


@require_DELETE
@login_required
def unsubscribe(request: AuthenticatedHttpRequest, podcast_id: int) -> TemplateResponse:
    """Unsubscribe user from a podcast."""
    podcast = get_object_or_404(
        Podcast.objects.published().filter(private=False), pk=podcast_id
    )
    request.user.subscriptions.filter(podcast=podcast).delete()
    messages.info(request, "Unsubscribed from Podcast")
    return _render_subscribe_action(request, podcast, is_subscribed=False)


def _render_subscribe_action(
    request: HttpRequest,
    podcast: Podcast,
    *,
    is_subscribed: bool,
) -> TemplateResponse:
    return TemplateResponse(
        request,
        "podcasts/detail.html#subscribe_button",
        {
            "podcast": podcast,
            "is_subscribed": is_subscribed,
        },
    )
